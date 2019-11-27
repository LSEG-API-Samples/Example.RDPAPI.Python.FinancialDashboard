# Sample Dash/Plotly financial dashboard application
# Author (Eikon version): Jason R
# Author (EDP version): Gurpreet B

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dte
import configparser as cp
import refinitiv.dataplatform as rdp
import json

dow30List = ['GS.N', 'NKE.N', 'CSCO.OQ', 'JPM.N', 'DIS.N', 'INTC.OQ', 'DOW.N', 'MRK.N', 'CVX.N', 'AXP.N', 'VZ.N', 'HD.N', 'WBA.OQ', 'XOM.N', 'MCD.N', 'UNH.N', 'KO.N', 'JNJ.N', 'MSFT.OQ', 'PG.N', 'IBM.N', 'PFE.N', 'MMM.N', 'AAPL.OQ', 'WMT.N', 'UTX.N', 'CAT.N', 'V.N', 'TRV.N', 'BA.N']
rtFields = ['DSPLY_NAME', 'TRDPRC_1', 'NETCHNG_1', 'HIGH_1', 'LOW_1', 'OPEN_PRC', 'HST_CLOSE', 'BID', 'ASK', 'ACVOL_1', 'EARNINGS', 'YIELD', 'PERATIO']
newsColumns = ['text', 'versionCreated']
esgColumns = ['Instrument', 'ESG Score', 'Environment Pillar Score', 'Social Pillar Score', 'Governance Pillar Score', 'Resource Use Score', 'Emissions Score', 'Innovation Score', 'Workforce Score', 'ESG Period Last Update Date']

app = dash.Dash('EDP Dashboard')
app.layout = html.Div([
	
	html.H4('Sample Dash/Financial App'),
	
	dcc.Dropdown(id='my-dropdown',
		options = [{'label': i, 'value': i} for i in dow30List],
		value = dow30List[0]
	),

	dcc.Loading(id="spinner-1", children=[html.Div(id="spinner-output-1")], type="circle", color='#FF0000'),
	dcc.Graph(id='my-graph'),

	html.H4('Streaming Prices'),
	html.Div(id='nop1'),
	html.Div(id='nop2'),
	dcc.Interval(id='interval', interval=1000),
	
	dte.DataTable(id='rtData',
		columns = [{'name': i, 'id': i} for i in rtFields]
	),
	
	html.H4('Environmental Social Governance'),
	dte.DataTable(id='esg',
		columns=[{"name": a, "id": a} for a in esgColumns] 
	),

	html.H4('News'),
	dte.DataTable(id='news', 
		columns=[{'name': i, 'id': i} for i in newsColumns], 
		style_as_list_view=True,
		style_cell={'textAlign': 'left'}, 
	),
	
	html.Div(children=[
		html.Button('Close', id='cButton'),
		dcc.Markdown(id='sText')
	], id='story', style={"display": "none"})
	
])



@app.callback([Output('news', 'data'), Output('my-graph', 'figure'), Output('esg', 'data'), Output("spinner-output-1", "children")], [Input('my-dropdown', 'value')])
def update_view(selected_dropdown_value):
	headlines = rdp.get_news_headlines(query = "L:EN and " + selected_dropdown_value, count = 10)
	
	history = rdp.get_historical_price_summaries(
		universe = selected_dropdown_value,
		interval = rdp.Intervals.DAILY,
		count = 360,
		fields=['TRDPRC_1']
	)

	history['SMA(20)'] = history['TRDPRC_1'].rolling(20).mean()
	history['SMA(45)'] = history.TRDPRC_1.rolling(45).mean()

	ts_result = {
		'data': [{
			'x': history.index.astype(str).tolist(),
			'y': history['TRDPRC_1'].values.tolist(),
			'name': 'Close'
		},
		{
			'x': history.index.astype(str).tolist(),
			'y': history['SMA(20)'].values.tolist(),
			'name': 'SMA20'
		},
		{
			'x': history.index.astype(str).tolist(),
			'y': history['SMA(45)'].values.tolist(),
			'name': 'SMA45'
		}],
		'layout': {'margin': {'l': 40, 'r': 0, 't': 20, 'b': 30}}
	}

	esgResponse = esgDataEndpoint.send_request(query_parameters = {"universe": selected_dropdown_value})
	if esgResponse.is_success:
		fd = esgResponse.data.raw
		headers = [h['title'] for h in fd['headers']]
		esg_result = [dict(zip(headers, fd['data'][0]))]
	else:
		esg_result = []
	
	return headlines.to_dict('records'), ts_result, esg_result, None



@app.callback([Output('story', 'style'), Output('sText', 'children')], [Input('news', 'active_cell')], [State('news', 'data')])
def update_rows(activeCell, data):
	if activeCell is not None:
		headline = data[activeCell['row']]['text']
		sID = data[activeCell['row']]['storyId']
		story = rdp.get_news_story(sID)
		if story is None:
			story = ''
		return {"display": "block", 'position': 'fixed', 'left': 100, 'top': 50, 'width': '800px', 'background': '#e2dfb7', 'border': '2px solid #202020'}, ('## ' + headline + '\n\n' + story)
	else:
		return {"display": "none"}, ''


@app.callback([Output('news', 'active_cell'), Output('news', 'selected_cells')], [Input('cButton', 'n_clicks')])
def show_modal(n):
	return None, []


@app.callback(Output('nop1', 'children'), [Input('my-dropdown', 'value')])
def startStreaming(selected_dropdown_value):
	global strm
	if strm is not None and strm.state == rdp.StreamState.Open:
		strm.close()
	strm = rdp.StreamingPrices(session = rdp.get_default_session(),
		universe = [selected_dropdown_value], 
		fields = rtFields,
	)
	strm.open()


@app.callback(Output('rtData', 'data'), [Input('interval', 'n_intervals')])
def update_realTimeData(n):
	global strm
	if strm is not None and strm.state == rdp.StreamState.Open:
		df = strm.get_snapshot_data()
		return df.to_dict('records')
	else:
		return []


# EDP configuration section
strm = None
config = cp.ConfigParser()
config.read("config.cfg")
rdp.open_platform_session(config['session']['app_key'], rdp.GrantPassword(username = config['session']['user'], password = config['session']['password']))
#rdp.open_desktop_session(config['session']['app_key'])
esgDataEndpoint = rdp.Endpoint(rdp.get_default_session(), "data/environmental-social-governance/v1/views/scores-standard")

# run the dash app
app.run_server(debug=True)
