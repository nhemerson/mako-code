
import plotly.express as px
import plotly.graph_objects as go
import traceback
from functions.lookups import FulfilColors
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Create legend options
class LegendOptions:
    top = dict(orientation="h", yanchor="bottom",
               y=1.02, xanchor="right", x=1),
    bottom = dict(orientation="h", yanchor="top",
                  y=-.13, xanchor="right", x=1)

# Set default appearance for plotly figures
def set_default_appearance_pre(fig,update_hovertemplate = False):
    fig.update_layout(
        height=500,
        margin=dict(l=10, r=10, t=40, b=10),
        legend_tracegroupgap=5,
        hovermode='x unified',
        legend=LegendOptions.bottom,
        hoverlabel=dict(bgcolor='rgba(255,255,255,0.75)', font=dict(
            color=FulfilColors.navy), bordercolor=FulfilColors.navy),
        title=dict(x=0, xanchor='left'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        modebar=dict(bgcolor='rgba(0,0,0,0)',
                     color=FulfilColors.navy, activecolor=FulfilColors.green),
        xaxis=dict(zeroline=True, zerolinewidth=1, zerolinecolor='rgb(235,235,235)',
                   showgrid=True, gridcolor='rgb(235,235,235)'),
        yaxis1=dict(rangemode='tozero', zeroline=True, zerolinewidth=1,
                    zerolinecolor='rgb(235,235,235)', gridcolor='rgb(235,235,235)'),
        yaxis2=dict(showgrid=False)
    )

    if update_hovertemplate is False:
        fig.update_traces(
            hovertemplate='%{y}'
        )
 
# Set default appearance for plotly figures
def set_default_appearance_post(fig):
    fig.update_layout() 

# Safely try to create a plotly chart
def safe_plotly_chart(chart):
    if type(chart) is str:  # error
        st.error(chart)
    else:
        try:
            st.plotly_chart(chart, use_container_width=True, config=dict(
                displaylogo=False,
                modeBarButtonsToRemove=["select", "select2d", "lasso", "lasso2d"],
                modeBarButtonsToAdd=["v1hovermode",
                                    "hoverclosest", "hovercompare", "togglehover"]
            ))
        except Exception:
            st.error('Error in Producing Chart')
            #st.error(chart)

#Make a bar chart
def make_bar_chart(
    title,
    df,
    x,
    y,
    x_label,
    y_label,
    color=None,
    add_cumulative=False,
    split_cumulative = False,
    trend_line=False,
    update_layout_args={},
    update_traces_args={},
    **kwargs
):
    """
    Makes a bar chart relating an 'x' to a 'y' column from a dataframe. 
    A 'color' category column can be specified to create different colored bars for each category.
    """

    try:

        fig = px.bar(df, x, y, color=color, title=title,
                     labels={x: x_label, y: y_label}, **kwargs)

        if color is None:
            fig.update_traces({'marker_color': FulfilColors.green})
        # else:
        #     fig.update_traces({'marker_color': FulfilColors.green})

        if add_cumulative:
            if split_cumulative is False:
                fig.add_trace(
                    go.Scatter(go.Scatter(name='Cumulative', x=df[x], y=np.cumsum(
                        df[y]), yaxis='y2', line_dash='dot', line_color=FulfilColors.navy))
                )

                fig.update_layout(
                    yaxis2=dict(title="Cumulative", range=[
                                0, df[y].sum()], anchor="x", overlaying="y", side='right')
                )
            else:
                #get unique color variables
                unique_color = df[color].unique()

                colormap = plt.cm.viridis

                max_cum_sum = 0 
                for i, color_value in enumerate(unique_color):
                    subset_df = df[df[color] == color_value]
                    
                    scatter_trace = go.Scatter(
                        name = f'{color_value} (cumu)',
                        x=subset_df[x],
                        y=np.cumsum(subset_df[y]),
                        mode='lines',
                        yaxis='y2', line_dash='dot',
                    )
                    
                    if subset_df[y].sum() > max_cum_sum:
                        max_cum_sum = subset_df[y].sum()
                    # Add scatter trace to the figure
                    fig.add_trace(scatter_trace)

                fig.update_layout(
                        yaxis2=dict(title="Cumulative", range=[
                                    0, max_cum_sum], anchor="x", overlaying="y", side='right')
                    )

        # add trendline
        if trend_line:
            scatter_data = px.scatter(df, x=x, y=y).data
            # Set the mode to 'lines' for the trend line
            scatter_data[0]['mode'] = 'lines'
            # Set the name of the trend line
            scatter_data[0]['name'] = 'Trend Line'
            fig.add_traces(scatter_data)

        set_default_appearance_pre(fig)
        fig.update_layout({'bargap': .05})
        fig.update_layout(**update_layout_args)
        fig.update_traces(**update_traces_args)
        set_default_appearance_post(fig)
        return fig

    except Exception:
        return f'Error making "{title}" bar chart. {traceback.format_exc()}'

# Histogram chart
def make_histogram(
    title,
    df,
    x,
    x_label,
    y_label,
    y=None,
    histfunc='count',  # { 'count', 'sum', 'avg' }
    color=None,
    color_label=None,
    add_cumulative=False,
    add_cumulative_split = False,
    plot_unique_cts=None,
    plot_unique_cts_label = None,
    plot_cts = None,
    plot_cts_label = None,
    bounds=None,
    #time_bin = None,
    update_layout_args={},
    update_traces_args={},
    **kwargs
):
    """
    Makes a histogram that uses 'histfunc' to aggregate an optional column 'y' over bins of a column 'x'.
    If 'y' is not specified, 'x' is used as both the binning variable 
    A 'color' category column can be specified to create different bars (aggregations) for each category in each bin.
    """

    try:
        df = df.dropna(axis=0, subset=[x])
        #st.write(df)
        if bounds is not None:
            df = df[(df[x] >= min(bounds)) & (df[x] <= max(bounds))]

        if color is not None:
            df = df.dropna(axis=0, subset=[color])

        if color_label is None:
            fig = px.histogram(df, x=x, y=y, histfunc=histfunc, color=color,
                            title=title, labels={x: x_label, y: y_label}, **kwargs)
        else:
            fig = px.histogram(df, x=x, y=y, histfunc=histfunc, color=color,
                            title=title, labels={x: x_label, y: y_label,color:color_label}, **kwargs)
            
        if color is None:
            fig.update_traces({'marker_color': FulfilColors.green})
        
        if add_cumulative:
            if add_cumulative_split is False:
                if y is None:
                    fig.add_trace(go.Scatter(
                        name='Cumulative', x=df.sort_values(x)[x], y=np.cumsum(np.ones((1, len(df)))),
                        yaxis='y2', line_dash='dot', line_color=FulfilColors.navy)
                    )
                else:
                    fig.add_trace(go.Scatter(
                        name='Cumulative', x=df.sort_values(x)[x], y=np.cumsum(df.sort_values(x)[y]),
                        yaxis='y2', line_dash='dot', line_color=FulfilColors.navy)
                    )
                fig.update_layout(
                    yaxis1=dict(title=y_label),
                    yaxis2=dict(title="Cumulative", domain=[
                                0, 1], anchor="x", overlaying="y", side='right')
                )
            else:
                distinct_color_value = list(df[color].unique())
                color_list = FulfilColors.cumulative_split_color_list
                for color_index in range(len(distinct_color_value)):
                    color_df = df[df[color] == distinct_color_value[color_index]]
                    if y is None:
                        fig.add_trace(go.Scatter(
                            name=f'Cumulative - {distinct_color_value[color_index]}', x=color_df.sort_values(x)[x], y=np.cumsum(np.ones((1, len(color_df)))),
                            yaxis='y2', line_dash='dot', line_color=color_list[color_index])
                        )
                    else:
                        fig.add_trace(go.Scatter(
                            name=f'Cumulative - {distinct_color_value[color_index]}', x=color_df.sort_values(x)[x], y=np.cumsum(color_df.sort_values(x)[y]),
                            yaxis='y2', line_dash='dot', line_color=color_list[color_index])
                        )
                    fig.update_layout(
                        yaxis1=dict(title=y_label),
                        yaxis2=dict(title="Cumulative", domain=[
                                    0, 1], anchor="x", overlaying="y", side='right')
                    )

        if plot_unique_cts is not None and fig.data[0].nbinsx is not None:
            for i in range(len(plot_unique_cts)):
                hist, bin_edges = np.histogram(pd.to_datetime(df[x]).view(np.int64), bins=fig.data[0].nbinsx,
                                               range=(min(df[x]).floor('1H').value, max(df[x]).ceil('1H').value))

                df['bin'], bin_edges = pd.cut(pd.to_datetime(df[x]).view(
                    np.int64), bin_edges, duplicates='drop', retbins=True)

                df_bin_unique = df.groupby('bin').agg(
                    {plot_unique_cts[i]: pd.Series.nunique}).reset_index()
                df_bin_unique[plot_unique_cts[i]] = df_bin_unique[plot_unique_cts[i]].fillna(0)
                if plot_unique_cts_label is None:
                    fig.add_trace(go.Scatter(
                        name=f'Unique {plot_unique_cts[i]}', x=[pd.to_datetime(interval.mid) for interval in df_bin_unique['bin']], y=df_bin_unique[plot_unique_cts[i]],
                        yaxis='y3', line_dash='dot')
                    )
                else:
                    fig.add_trace(go.Scatter(
                        name=f'Unique {plot_unique_cts_label[i]}', x=[pd.to_datetime(interval.mid) for interval in df_bin_unique['bin']], y=df_bin_unique[plot_unique_cts[i]],
                        yaxis='y3', line_dash='dot')
                    )
            fig.update_layout(
                xaxis=dict(domain=[.05, 1]),
                yaxis1=dict(side='left', position=.05,
                            gridcolor='rgb(235,235,235)'),
                yaxis3=dict(title='Unique counts', domain=[
                            0, 1], anchor='free', overlaying="y", side='left', position=0, showgrid=False),
            )

        fig.update_yaxes(rangemode='tozero')

        set_default_appearance_pre(fig)
        fig.update_layout({'bargap': .05})
        fig.update_traces(
            hovertemplate='  %{x}  %{y}'
        )
        fig.update_layout(**update_layout_args)
        fig.update_traces(**update_traces_args)
        set_default_appearance_post(fig)
        return fig

    except Exception:
        return f'Error making {title} histogram. {traceback.format_exc()}'
    

# Make a line chart
def make_line_chart(
    title,
    df,
    x,
    y,
    x_label,
    y_label,
    color=None,
    color_label = None,
    markers=True,
    sample_annotations=None,
    update_layout_args={},
    update_traces_args={},
    **kwargs
):
    """
    Makes a line chart relating an 'x' to a 'y' column from a dataframe. 
    A 'color' category column can be specified to create different colored lines for each category.
    """

    try:
        if color_label is None:
            fig = px.scatter(df, x=x, y=y, color=color, title=title,
                            labels={x: x_label, y: y_label}, hover_data=sample_annotations, **kwargs)
        else:
            fig = px.scatter(df, x=x, y=y, color=color, title=title,
                            labels={x: x_label, y: y_label,color:color_label}, hover_data=sample_annotations, **kwargs)

        if color is None:
            fig.update_traces({'marker_color': FulfilColors.green,
                               'line_color': FulfilColors.green})

        set_default_appearance_pre(fig)
        fig.update_traces(mode='lines', connectgaps=True)
        if markers:
            fig.update_traces(marker=dict(size=4), mode='lines+markers')
        fig.update_layout(**update_layout_args)
        fig.update_traces(**update_traces_args)
        set_default_appearance_post(fig)
        return fig

    except Exception:
        return f'Error making "{title}" line chart. {traceback.format_exc()}'


def make_multiline_chart(
    title,
    df,
    x,
    ys,
    x_label,
    y_label,
    orig_df_color=None,
    transpose_xy=False,
    new_labels=None,
    markers=True,
    fill=None,
    ys_colors=None,
    update_layout_args={},
    update_traces_args={},
    **kwargs
):
    """
    Makes a line chart relating an 'x' column to multiple 'y' columns from a dataframe.
    An 'orig_df_color' category column can be specified to create unique colored lines for every (y column, unique category column value) pair.
    """

    try:

        if orig_df_color is None:
            df_melt = pd.melt(df, id_vars=[x], value_vars=ys)
        else:
            df_melt = pd.melt(df, id_vars=[x, orig_df_color], value_vars=ys)
            df_melt['variable'] = df_melt[orig_df_color].astype(
                str) + ": " + df_melt['variable']

        if 'legend' in update_layout_args:
            # removes the legend title "variable"
            update_layout_args['legend']['title_text'] = ''
        else:
            update_layout_args['legend'] = dict(title_text='')

        if transpose_xy:
            fig = make_line_chart(title=title, df=df_melt, x='value', y=x, color='variable',
                                  x_label=x_label, y_label=y_label, markers=markers,
                                  update_layout_args=update_layout_args, update_traces_args=update_traces_args, **kwargs)
        else:
            if fill:
                fig = go.Figure()
                if ys_colors == None:
                    ys_colors = []
                    for i in len(0, len(ys)):
                        ys_colors.append(FulfilColors.green)
                for y in range(0, len(ys)):
                    if y == 0:
                        trace = go.Scatter(go.Scatter(x=df[x], y=df[ys[y]]), name=ys[y],
                                           mode='markers + lines', marker_color=ys_colors[y])
                    else:
                        trace = go.Scatter(go.Scatter(x=df[x], y=df[ys[y]]), name=ys[y],
                                           mode='markers + lines', marker_color=ys_colors[y], fill=fill)
                    fig.add_trace(trace)

            # for x in np.arange(len(ys)):

            else:
                fig = make_line_chart(title=title, df=df_melt, x=x, y='value', color='variable',
                                      x_label=x_label, y_label=y_label, markers=markers, update_layout_args=update_layout_args, update_traces_args=update_traces_args, **kwargs)
            # fig = make_line_chart(title=title, df=df_melt, x=x, y='value', color='variable',
            #                       x_label=x_label, y_label=y_label, markers=markers,
            #                       update_layout_args=update_layout_args, update_traces_args=update_traces_args, **kwargs)

        if new_labels is not None and len(ys) == len(new_labels) and orig_df_color is None:
            new_label_dict = dict(zip(ys, new_labels))
            fig.for_each_trace(lambda trace:
                               trace.update(
                                   name=new_label_dict[trace.name],
                                   legendgroup=new_label_dict[trace.name],
                                   hovertemplate=trace.hovertemplate.replace(
                                       trace.name, new_label_dict[trace.name])
                               )
                               )

        # if new_labels is not None and len(ys) == len(new_labels):
        #     replacements = dict(zip(ys, new_labels))
        #     fig.for_each_trace(
        #         lambda trace: replace_trace_names(trace, replacements))
        return fig

    except Exception:
        return f'Error making "{title}" multiline chart. {traceback.format_exc()}'

# Make a scatter plot
def make_scatter_chart(
    title,
    df,
    x,
    y,
    x_label,
    y_label,
    color=None,
    add_cumulative=False,
    sample_annotations=None,
    update_layout_args={},
    update_traces_args={},
    **kwargs
):
    """
    Makes a scatter chart relating 'x' and 'y' columns from a dataframe. 
    A 'color' category column can be specified to create different colored scatters for each category.
    """

    try:
        
        fig = px.scatter(df, x=x, y=y, color=color, title=title, labels={
                x: x_label, y: y_label}, hover_data=sample_annotations, opacity=0.7, **kwargs)
        
        set_default_appearance_pre(fig)

        if color is None:
            fig.update_traces({'marker_color': FulfilColors.green,
                               'line_color': FulfilColors.green})

        if add_cumulative:
            fig.add_trace(
                go.Scatter(go.Scatter(name='Cumulative', x=df[x], y=np.cumsum(
                    df[y]), yaxis='y2', line_dash='dot', line_color=FulfilColors.navy))
            )
            fig.update_layout(
                yaxis2=dict(title="Cumulative", range=[
                            0, df[y].sum()], anchor="x", overlaying="y", side='right')
            )

        fig.update_traces(marker=dict(size=4))
        fig.update_layout(**update_layout_args)
        fig.update_traces(**update_traces_args)
        set_default_appearance_post(fig)
        return fig

    except Exception:
        return f'Error making "{title}" scatter chart. {traceback.format_exc()}'

# Make pareto chart
def make_pareto(
    title,
    df,
    y,
    y_label,
    x_label,
    sort_by=None,
    sort_ascending=False,
    y_bounds=None,
    sort_by_bounds=None,
    sample_annotations=None,
    update_layout_args={},
    update_traces_args={},
    **kwargs
):
    """
    Makes a pareto chart: a scatter of 'y' column values against their magnitude rank or optionally rank by 'sort_by' column values.
    Value sorting is descending by default.
    """

    try:
        df = df.dropna(axis=0, subset=[y])

        if y_bounds is not None:
            df = df[(df[y] >= min(y_bounds)) & (df[y] <= max(y_bounds))]

        if sort_by is not None:
            df = df.dropna(axis=0, subset=[sort_by])
            df = df.sort_values([sort_by, y], ascending=sort_ascending)
            if sort_by_bounds is not None:
                df = df[(df[sort_by] >= min(sort_by_bounds)) &
                        (df[sort_by] <= max(sort_by_bounds))]
        else:
            df = df.dropna(axis=0, subset=[y]).sort_values(
                y, ascending=sort_ascending)

        x = list(range(1, len(df) + 1))
        sumy = df[y].sum()
        cumsumy = df[y].cumsum()

        fig = go.Figure()
        set_default_appearance_pre(fig)

        if sample_annotations is None:
            sample_annotations = []
        if sort_by is not None and sort_by not in sample_annotations:
            sample_annotations.insert(0, sort_by)
        if len(sample_annotations) > 0:
            fig.add_traces([
                go.Scatter(x=x, y=df[y], name='', yaxis='y1', opacity=0, customdata=np.stack(
                    [df[a].astype(str) for a in sample_annotations], axis=-1)),
            ])
            hovertemplate = ''
            idx = 0
            for a in sample_annotations:
                hovertemplate += f'<b>{a}:</b>' + \
                    ' %{customdata[' + f'{idx}' + ']}<br>'
                idx += 1
            fig.update_traces(hovertemplate=hovertemplate)

        fig.add_traces([
            go.Scatter(x=x, y=df[y], name=y_label, yaxis='y1', mode='markers+lines',
                       marker_size=3, line_width=1, line_color=FulfilColors.green),
            go.Scatter(x=x, y=cumsumy, name='Cumulative', yaxis='y2', mode='lines',
                       line_width=1, line_color=FulfilColors.navy, line_dash='dot'),
            go.Scatter(x=x, y=cumsumy / sumy, name='Cumulative %',
                       yaxis='y3', mode='lines', opacity=0, showlegend=False),
        ])
        fig.add_annotation(text="Cumulative", xref="paper",
                           yref="paper", x=1.03, y=-.17, showarrow=False)
        fig.add_annotation(text="Sum", xref="paper", yref="paper",
                           x=.97, y=-.12, showarrow=False)
        fig.add_annotation(text="Sum %", xref="paper",
                           yref="paper", x=1.03, y=-.12, showarrow=False)

        fig.update_layout(
            title=title,
            xaxis=dict(title=x_label, domain=[0, .95]),
            yaxis1=dict(title=y_label, side='left', position=0),
            yaxis2=dict(title='', anchor="free", overlaying="y",
                        side='right', position=.95, showgrid=False),
            yaxis3=dict(title='', tickformat='.1%', anchor="free",
                        overlaying="y", side='right', position=1, showgrid=False),
            legend=dict(y=-.2)
        )
        fig.update_layout(**update_layout_args)
        fig.update_traces(**update_traces_args)
        set_default_appearance_post(fig)
        return fig

    except Exception:
        #return st.error(f'Error making "{title}" pareto. {traceback.format_exc()}')
        return f'Error making "{title}" pareto. {traceback.format_exc()}'