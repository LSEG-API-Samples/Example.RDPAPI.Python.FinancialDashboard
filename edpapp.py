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
from functools import reduce


# define data to be displayed
chartRange = range(2010, 2020)
dow30List = ['GS.N', 'NKE.N', 'CSCO.OQ', 'JPM.N', 'DIS.N', 'INTC.OQ', 'DOW.N', 'MRK.N', 'CVX.N', 'AXP.N', 'VZ.N', 'HD.N', 'WBA.OQ', 'XOM.N', 'MCD.N', 'UNH.N', 'KO.N', 'JNJ.N', 'MSFT.OQ', 'PG.N', 'IBM.N', 'PFE.N', 'MMM.N', 'AAPL.OQ', 'WMT.N', 'UTX.N', 'CAT.N', 'V.N', 'TRV.N', 'BA.N']
newsColumns = [{"name": 'News', "id": 'text'}, {"name": 'Date', "id": 'date'},]
fiColumns = ['Instrument', 'Net sales', 'Gross Profit Margin - %', 'Operating Margin - %', 'EBITDA', 'EPS', 'ROA', 'ROE']


#Layout App Compnents - Inputs, Outputs etc
app = dash.Dash('EDP Dashboard')
app.layout = html.Div([
	
	html.H4('Sample Dash/Financial App'),
	
	dcc.Dropdown(id='my-dropdown',
		options = [{'label': i, 'value': i} for i in dow30List],
		value = dow30List[0]
	),
	
	dcc.Loading(id="spinner-1", children=[html.Div(id="spinner-output-1")], type="circle", color='#FF0000'),
	
	html.Div([
		html.Div([
			dcc.Graph(id='my-graph', figure={ 'data': [],
				'layout': {'margin': {'l': 40, 'r': 0, 't': 20, 'b': 30}, 'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)'}
				}),
			dcc.RangeSlider(
				id = 'year-slider',
				min = min(chartRange),
				max = max(chartRange),
				value = [max(chartRange), max(chartRange)],
				marks = {str(year): str(year) for year in chartRange},
				step = None
			)
		], className="eight columns", style={'paddingBottom': 10}),

		html.Div([
			html.H4('Streaming Prices'),
			html.Div(id='nop'),
			dte.DataTable(id='rtData',
				columns=[{"name": 'a', "id": 'a'}, {"name": 'b', "id": 'b'}, {"name": 'c', "id": 'c'}, {"name": 'd', "id": 'd'}], 
				style_cell={'textAlign': 'left', 'border': 'None', 'backgroundColor': '#1a1c23'}, 
				style_header={ 'display': 'None' },
				style_data_conditional=[{
					'if': {'column_id': bold},
						'fontWeight': 'bold'
				} for bold in ['a', 'c']]
			),
			dcc.Interval(id='interval', interval=1000),

			html.H4('Financial Ratios'),
			dte.DataTable(id='finRatios',
				columns=[{"name": 'a', "id": 'a'}, {"name": 'b', "id": 'b'}], 
				style_cell={'textAlign': 'left', 'border': 'None', 'backgroundColor': '#1a1c23'}, 
				style_header={ 'display': 'None' },
				style_data_conditional=[{
					'if': {'column_id': 'a'},
					'fontWeight': 'bold'
				}]
			)
			
		], className="four columns"),
	], className="row"),
	
	html.H4('Latest Headlines'),
	dte.DataTable(columns=newsColumns, 
		id='news', 
		style_cell={'textAlign': 'left', 'border': '1px solid #404040', 'backgroundColor': '#1a1c23'}, 
		style_as_list_view=True,
		style_header={'fontWeight': 'bold'},
	)
])


@app.callback([Output('news', 'data'), Output('finRatios', 'data'), Output('my-graph', 'figure'), Output("spinner-output-1", "children")], [Input('my-dropdown', 'value')], [State('year-slider', 'value')])
def update_view(selected_dropdown_value, selected_years):
	response = newsEndpoint.send_request(query_parameters = {"query": "L:EN and " + selected_dropdown_value})
	if response.is_success:
		hlns = response.json()['data']
		news_result = [{"date": hl['newsItem']['itemMeta']['versionCreated']['$'], "text": hl['newsItem']['itemMeta']['title'][0]['$']} for hl in hlns]
	else:
		news_result = []
		
	response = fDataEndpoint.send_request(query_parameters = {"universe": selected_dropdown_value})
	if response.is_success:
		fd = response.json()
		headers = [h['title'] for h in fd['headers']]
		zp = zip(headers, fd['data'][0])
		fin_result = [{'a': x, 'b': y} for x, y in zp if x in fiColumns]
	else:
		fin_result = []
		
	response = tsEndpoint.send_request(path_parameters = {'instrument': selected_dropdown_value}, query_parameters = {'interval': 'P1D', 'fields': 'TRDPRC_1', 'start': str(selected_years[0]) + '-01-01', 'end': str(selected_years[1]) + '-12-31'})
	if response.is_success:
		ts = response.json()
		datesM = [x for x, y in ts[0]['data']]
		xM = [y for x, y in ts[0]['data']]
		N = 10 * (selected_years[1] - selected_years[0] + 1)
		sma = [None for i in range(N - 1)]
			
		for i in range(0, len(xM) - N - 1, 1):
			y = xM[i: i + N]
			dPt = reduce(lambda x, y__: x + y__, y) / len(y)
			sma.append(dPt)
	
		ts_result = {'data': [{'x': datesM, 'y': xM, 'name': 'Close'}, {'x': datesM, 'y': sma, 'name': 'SMA'}], 'layout': {'margin': {'l': 40, 'r': 0, 't': 20, 'b': 30}, 'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)'}}
	else:
		ts_result = {'data': []}
	
	return news_result, fin_result, ts_result, None


@app.callback(Output('nop', 'children'), [Input('my-dropdown', 'value')])
def startStreaming(selected_dropdown_value):
	global strm
	if strm is not None and strm.state == rdp.StreamState.Open:
		strm.close()
	strm = pricing.open_stream(
		universe = selected_dropdown_value, 
		fields = ['DSPLY_NAME', 'TRDPRC_1', 'NETCHNG_1', 'HIGH_1', 'LOW_1', 'OPEN_PRC', 'HST_CLOSE', 'BID', 'ASK', 'ACVOL_1', 'EARNINGS', 'YIELD', 'PERATIO'],
	)


@app.callback(Output('rtData', 'data'), [Input('interval', 'n_intervals')])
def update_realTimeData(n):
	global strm
	if strm is not None and strm.state == rdp.StreamState.Open:
		return [
			{'a': 'Last', 'b': strm.get_field_value('TRDPRC_1'), 'c': 'Volume', 'd': strm.get_field_value('ACVOL_1')},
			{'a': 'Bid', 'b': strm.get_field_value('BID'), 'c': 'Ask', 'd': strm.get_field_value('ASK')},
			{'a': 'High', 'b': strm.get_field_value('HIGH_1'), 'c': 'Low', 'd': strm.get_field_value('LOW_1')},
			{'a': 'Open', 'b': strm.get_field_value('OPEN_PRC'), 'c': 'Close', 'd': strm.get_field_value('HST_CLOSE')},
		]
	else:
		return []


# EDP configuration section
strm = None
config = cp.ConfigParser()
config.read("config.cfg")

rrSession = rdp.PlatformSession(config['session']['app_key'], rdp.GrantPassword(username = config['session']['user'], password = config['session']['password']))
rrSession.open()

newsEndpoint = rdp.Endpoint(rrSession, "data/news/v1/headlines")
fDataEndpoint = rdp.Endpoint(rrSession, "data/company-fundamentals/beta1/views/financial-summary-brief")
tsEndpoint = rdp.Endpoint(rrSession, "data/historical-pricing/v1/views/interday-summaries/{instrument}")
pricing = rdp.Pricing(rrSession)

# run the dash app
app.run_server(debug=True)
