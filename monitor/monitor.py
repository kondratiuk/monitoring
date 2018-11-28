import datetime
import platform

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly
import psutil
from dash.dependencies import Input, Output

colors = {
    'background': '#d8ecff',
    'text': '#008000'
}
refresh_period = 1
to_sec = 1000
history_points = 60

app = dash.Dash(__name__)
app.layout = html.Div(children=[
    html.Div([
        html.H2('Activity Dashboards', style={'color': 'green', 'text-align': 'center'}),
        html.H3('General information'),
        html.P('Platform: ' + platform.platform()),
        html.P('Processor: ' + platform.processor()),
        html.P('Computer name: ' + platform.node()),
        html.P('Connected users: ' + '{}'.format(psutil.users().__len__())),
        html.P('Python version: ' + platform.python_version())
    ]),
    html.Div([
        html.H3('CPU statistics'),
        html.Div(id='cpu-update-text'),
        dcc.Graph(id='cpu-update-graph'),
        dcc.Interval(
            id='cpu-interval-component',
            interval=refresh_period * to_sec,
            n_intervals=0
        )
    ]),
    html.Div([
        html.H3('Memory statistics'),
        html.Div(id='mem-update-text'),
        dcc.Graph(id='mem-update-graph'),
        dcc.Interval(
            id='mem-interval-component',
            interval=refresh_period * to_sec,
            n_intervals=0
        )
    ]),
    html.Div([
        html.H3('Ethernet statistics'),
        html.Div(id='net-update-text'),
        dcc.Graph(id='net-update-graph'),
        dcc.Interval(
            id='net-interval-component',
            interval=refresh_period * to_sec,
            n_intervals=0
        )
    ]),
    html.Div([
        html.H3('Current process statistics'),
        html.Div(id='proc-update-text'),
        dcc.Graph(id='proc-update-graph'),
        dcc.Interval(
            id='proc-interval-component',
            interval=refresh_period * to_sec,
            n_intervals=0
        )
    ])
],
    style={'backgroundColor': colors['background'], 'color': colors['text']}
)


class Context:
    def __init__(self):
        self.t = []
        self.cpu = []
        self.per_cpu = [[] for x in range(psutil.cpu_count())]
        self.mem = []
        self.disk = []
        self.pids = []
        self.bytes_sent = []
        self.bytes_recv = []
        self.errin = []
        self.errout = []
        self.proc_mem = []
        self.proc_num_threads = []
        self.proc_open_files = []
        self.proc_conn = []

    @classmethod
    def append_data(cls, data_one, data_two):
        n = len(data_one)
        if n > history_points:
            del data_one[0:n - history_points - 1]
        data_one.append(data_two)


context = Context()
text_style = {'padding': '10px', 'fontSize': '18px'}
to_mb = pow(1000, 2)  # not 1024
to_gb = pow(1024, 3)


def get_figure_layout(rows, cols, range1, range2):
    fig = plotly.tools.make_subplots(rows=rows, cols=cols, vertical_spacing=0.2)
    fig['layout']['margin'] = {'l': 150, 'r': 150, 'b': 50, 't': 50}
    fig['layout']['plot_bgcolor'] = colors['background']
    fig['layout']['paper_bgcolor'] = colors['background']
    fig['layout']['font'] = {'color': colors['text']}
    fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}
    if range1 != -1:
        fig['layout']['yaxis1'].update(range=[0, range1])
    if range2 != -1:
        fig['layout']['yaxis2'].update(range=[0, range2])
    return fig


# CPUs
@app.callback(Output('cpu-update-text', 'children'),
              [Input('cpu-interval-component', 'n_intervals')])
def metrics_cpu(self):
    speed = psutil.cpu_freq()
    return [
        html.Div([
            html.Span('CPU utilization: {} %'.format(context.cpu[-1]), style=text_style),
            html.Span('Cores: {}'.format(psutil.cpu_count(logical=False)), style=text_style),
            html.Span('Logical CPUs: {}'.format(psutil.cpu_count()), style=text_style)
        ]),
        html.Span('Speed: {} GHz'.format(speed[0]), style=text_style),
        html.Span('Maximum speed: {} GHz'.format(speed[2]), style=text_style)
    ]


@app.callback(Output('cpu-update-graph', 'figure'),
              [Input('cpu-interval-component', 'n_intervals')])
def graph_cpu(self):
    context.append_data(context.t, datetime.datetime.now())
    context.append_data(context.cpu, psutil.cpu_percent())
    for data, pcnt in zip(context.per_cpu, psutil.cpu_percent(percpu=True)):
        context.append_data(data, pcnt)

    fig = get_figure_layout(2, 1, 100, 100)

    for i, y in enumerate(context.per_cpu):
        fig.append_trace({
            'x': context.t,
            'y': y,
            'name': 'cpu {}'.format(i),
            'mode': 'lines',
            'type': 'scatter',
        }, 1, 1),
    fig.append_trace({
        'x': context.t,
        'y': context.cpu,
        'name': 'CPU',
        'mode': 'lines+markers',
        'type': 'scatter',
        'fill': 'tozeroy',
    }, 2, 1)

    return fig


# Memory and PIDs
@app.callback(Output('mem-update-text', 'children'),
              [Input('mem-interval-component', 'n_intervals')])
def metrics_mem(self):
    vm = psutil.virtual_memory()
    vm_total = format(vm[0] / to_gb, '.2f')
    vm_avail = format(vm[1] / to_gb, '.2f')
    vm_used = format(vm[3] / to_gb, '.2f')

    disk = psutil.disk_usage('/')
    disk_total = format(disk[0] / to_gb, '.2f')
    disk_used = format(disk[1] / to_gb, '.2f')
    disk_free = format(disk[2] / to_gb, '.2f')

    return [
        html.Div([
            html.Span('Memory usage: {} %'.format(context.mem[-1]), style=text_style),
            html.Span('Total: {} GB'.format(vm_total), style=text_style),
            html.Span('Available: {} GB'.format(vm_avail), style=text_style),
            html.Span('Used: {} GB'.format(vm_used), style=text_style)
        ]),
        html.Div([
            html.Span('Disk usage: {} %'.format(context.disk[-1]), style=text_style),
            html.Span('Total: {} GB'.format(disk_total), style=text_style),
            html.Span('Used: {} GB'.format(disk_used), style=text_style),
            html.Span('Free: {} GB'.format(disk_free), style=text_style)
        ]),
        html.Span('PIDs: {}'.format(context.pids[-1]), style=text_style)
    ]


@app.callback(Output('mem-update-graph', 'figure'),
              [Input('mem-interval-component', 'n_intervals')])
def graph_mem(self):
    context.append_data(context.mem, psutil.virtual_memory().percent)
    context.append_data(context.disk, psutil.disk_usage('/').percent)
    context.append_data(context.pids, psutil.pids().__len__())

    fig = get_figure_layout(1, 3, 100, 100)

    fig.append_trace({
        'x': context.t,
        'y': context.mem,
        'name': 'Memory usage',
        'mode': 'lines',
        'type': 'scatter',
        'fill': 'tozeroy',
    }, 1, 1)
    fig.append_trace({
        'x': context.t,
        'y': context.disk,
        'name': 'Disk usage',
        'mode': 'lines',
        'type': 'scatter',
        'fill': 'tozeroy',
    }, 1, 2)
    fig.append_trace({
        'x': context.t,
        'y': context.pids,
        'name': 'PIDs',
        'mode': 'lines',
        'type': 'scatter',
        'fill': 'tozeroy',
    }, 1, 3)

    return fig


# Ethernet
@app.callback(Output('net-update-text', 'children'),
              [Input('net-interval-component', 'n_intervals')])
def metrics_net(self):
    sent, erout = format(context.bytes_sent[-1] / to_mb, '.2f'), context.errout[-1]
    rcv, erin = format(context.bytes_recv[-1] / to_mb, '.2f'), context.errin[-1]

    return [
        html.Span('Bytes sent: {} MB with {} errors'.format(sent, erout), style=text_style),
        html.Span('Bytes received: {} MB with {} errors'.format(rcv, erin), style=text_style),
        #html.Span('Speed: {} MB/s'.format(psutil.net_if_stats().get('Ethernet')[2]), style=text_style) # if exists
    ]


@app.callback(Output('net-update-graph', 'figure'),
              [Input('net-interval-component', 'n_intervals')])
def graph_net(self):
    net_io = psutil.net_io_counters()
    context.append_data(context.bytes_sent, net_io[0])
    context.append_data(context.bytes_recv, net_io[1])
    context.append_data(context.errin, net_io[4])
    context.append_data(context.errout, net_io[5])

    fig = get_figure_layout(2, 2, -1, -1)

    fig.append_trace({
        'x': context.t,
        'y': context.bytes_sent,
        'name': 'Bytes sent',
        'mode': 'lines+markers',
        'type': 'scatter',
    }, 1, 1)
    fig.append_trace({
        'x': context.t,
        'y': context.bytes_recv,
        'name': 'Bytes received',
        'mode': 'lines+markers',
        'type': 'scatter',
    }, 1, 2)
    fig.append_trace({
        'x': context.t,
        'y': context.errin,
        'name': 'Errors while receiving',
        'mode': 'lines+markers',
        'type': 'scatter',
    }, 2, 1)
    fig.append_trace({
        'x': context.t,
        'y': context.errout,
        'name': 'Errors while sending',
        'mode': 'lines+markers',
        'type': 'scatter',
    }, 2, 2)

    return fig


# Current process
@app.callback(Output('proc-update-text', 'children'),
              [Input('proc-interval-component', 'n_intervals')])
def metrics_proc(self):
    return [
        html.Span('Process memory: {} %'.format(context.proc_mem[-1]), style=text_style),
        html.Span('Thread number: {}'.format(context.proc_num_threads[-1]), style=text_style),
        html.Span('Open files: {}'.format(context.proc_open_files[-1]), style=text_style),
        html.Span('Socket connections: {}'.format(context.proc_conn[-1]), style=text_style)
    ]


@app.callback(Output('proc-update-graph', 'figure'),
              [Input('proc-interval-component', 'n_intervals')])
def graph_proc(self):
    proc = psutil.Process()
    context.append_data(context.proc_mem, format(proc.memory_percent(), '.2f'))
    context.append_data(context.proc_num_threads, proc.num_threads())
    context.append_data(context.proc_open_files, proc.open_files().__len__())
    context.append_data(context.proc_conn, proc.connections().__len__())

    fig = get_figure_layout(2, 2, -1, -1)

    fig.append_trace({
        'x': context.t,
        'y': context.proc_mem,
        'name': 'Process memory',
        'mode': 'lines',
        'type': 'scatter',
        'fill': 'tozeroy',
    }, 1, 1)
    fig.append_trace({
        'x': context.t,
        'y': context.proc_num_threads,
        'name': 'Thread number',
        'mode': 'lines',
        'type': 'scatter',
        'fill': 'tozeroy',
    }, 1, 2)
    fig.append_trace({
        'x': context.t,
        'y': context.proc_open_files,
        'name': 'Open files',
        'mode': 'lines',
        'type': 'scatter',
        'fill': 'tozeroy',
    }, 2, 1)
    fig.append_trace({
        'x': context.t,
        'y': context.proc_conn,
        'name': 'Socket connections',
        'mode': 'lines',
        'type': 'scatter',
        'fill': 'tozeroy',
    }, 2, 2)

    return fig


if __name__ == '__main__':
    app.run_server(debug=False)
