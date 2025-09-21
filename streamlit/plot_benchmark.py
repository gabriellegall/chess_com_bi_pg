import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_processing import get_player_metric_values

def render_metric_boxplot(df: pd.DataFrame, metric: str, value_all: float, value_specific: float, left_annotation: str, right_annotation: str, last_n_games: int):
    """
    Renders a boxplot given an input dataframe `df`, and highlights two hard-coded values:
    - `value_all` 
    - `value_specific` (with the `last_n_games` information on hover)
    It also takes care of the annotations for the min and max values on the x-axis (`left_annotation`, `right_annotation`).
    """
    df_plot = df.copy()
    df_plot['category'] = 'Player Distribution' # Hard coded constant used as a Y-axis

    fig = px.box(
        df_plot,
        x=metric,
        y="category",
        labels={metric: metric.replace('_', ' ').title(), "category": ""},
        orientation='h',
        hover_data=['username']
    )

    # Replace the default box plot with one that has jittered points and better colors for dark theme
    fig.data[0].update(
        boxpoints='all', 
        jitter=0.3,
        pointpos=0,
        marker_color='rgba(0, 191, 255, 0.7)', 
        marker_size=5,
        fillcolor='rgba(0, 191, 255, 0.5)',
        line_color='rgba(0, 191, 255, 1)'
    )

    # Highlight value_all
    if value_all is not None:
        fig.add_trace(go.Scatter(
            x=[value_all],
            y=['Player Distribution'], 
            mode="markers",
            marker=dict(color="yellow", size=20, symbol="line-ns", line=dict(width=3, color='yellow')),
            name="Overall",
            showlegend=False
        ))
    
    # Highlight value_specific
    if value_specific is not None:
        fig.add_trace(go.Scatter(
            x=[value_specific],
            y=['Player Distribution'],
            mode="markers",
            marker=dict(color="yellow", size=15, symbol="star", line=dict(width=1, color='black')),
            name=f"Last {last_n_games} Games",
            showlegend=False
        ))

    fig.update_layout(
        yaxis=dict(title="", showticklabels=False),
        xaxis_title="",
        xaxis_tickformat=".0%",
        showlegend=True,
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.7)'),
        height=200,
        title=dict(text="")
    )

    # Annotate min/max
    x_min = df_plot[metric].min()
    x_max = df_plot[metric].max()
    fig.add_annotation(x=x_min, y=-0.4, text=left_annotation, showarrow=False, font=dict(color="white"))
    fig.add_annotation(x=x_max, y=-0.4, text=right_annotation, showarrow=False, font=dict(color="white"))

    st.plotly_chart(fig, use_container_width=True)

def render_legend(username, last_n_games):
    """
    Renders a custom legend once for all box plots.
    This legend describes the two markers in the boxplots (`value_all`, `value_specific`).
    """
    legend_html = f"""
    <div style="display: flex; align-items: center; justify-content: flex-start; gap: 25px; font-size: 14px; padding: 1px 0 1px 15px; margin-bottom: 15px;">
        <span style="font-weight: bold;">Legend:</span>
        <div style="display: flex; align-items: center;">
            <span style="color: yellow; font-size: 25px; font-weight: bold; margin-right: 8px;">|</span>
            <span>All games by {username}</span>
        </div>
        <div style="display: flex; align-items: center;">
            <span style="color: yellow; font-size: 20px; margin-right: 8px;">★</span>
            <span>Last {last_n_games} games by {username}</span>
        </div>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)

def prepare_section_plot_data(section_config: list, plot_config: dict, df_filtered: pd.DataFrame, username_to_highlight: str, last_n_games: int) -> list[dict]:
    """
    Creates a list of dictionaries with all the elements needed to render the boxplots and breakdowns boxplots.
    Each row in the list represents one row of `section_config`, which is a section in the page (e.g. 'Throws') composed of several main plots and optional breakdown subplots.
    The `plot_config` argument is used to describe how the metrics of each plot should be aggregated, the titles, axis labels, etc.
    The values to highlight (`value_all`, `value_specific`) are pre-calculated based on the input `df_filtered`, `username_to_highlight` and `last_n_games`.
    """
    prepared_data = []
    for config_item in section_config:
        title = config_item['title']
        metrics = config_item['metrics']
        help_text = config_item.get('help_text') or plot_config.get(metrics[0], {}).get('help')

        prepared_section_data = {
            'title': title,
            'help_text': help_text,
            'metrics': {},
            'has_breakdown': config_item['has_breakdown'],
            'breakdown_metrics': {}
        }

        # Calculate main metric values
        for metric in metrics:
            config = plot_config[metric]
            value_all, value_specific = get_player_metric_values(
                df_filtered, metric, username_to_highlight, config['agg'], last_n_games=last_n_games
            )
            prepared_section_data['metrics'][metric] = {
                'config': config,
                'value_all': value_all,
                'value_specific': value_specific
            }

        # Calculate breakdown metric values if applicable
        if prepared_section_data['has_breakdown']:
            breakdown_groups = config_item['breakdown_groups']
            for parent_metric, breakdown_metric_list in breakdown_groups.items():
                prepared_section_data['breakdown_metrics'][parent_metric] = {}
                for metric in breakdown_metric_list:
                    config = plot_config[metric]
                    value_all, value_specific = get_player_metric_values(
                        df_filtered, metric, username_to_highlight, config['agg'], last_n_games=last_n_games
                    )
                    prepared_section_data['breakdown_metrics'][parent_metric][metric] = {
                        'config': config,
                        'value_all': value_all,
                        'value_specific': value_specific
                    }
        
        prepared_data.append(prepared_section_data)
    return prepared_data

def render_plot_section(prepared_section_data: dict, df_player_agg: pd.DataFrame, last_n_games: int):
    """
    Renders the boxplots for a section in the page (e.g. 'Throws') composed of several main plots and optional breakdown subplots.
    All the necessary information is pre-calculated under the dictionary `prepared_section_data`.
    """
    st.subheader(prepared_section_data['title'], help=prepared_section_data['help_text'])

    # Boxplot rendering
    metrics = list(prepared_section_data['metrics'].keys())
    cols = st.columns(len(metrics))
    for col, metric in zip(cols, metrics):
        with col:
            data = prepared_section_data['metrics'][metric]
            config = data['config']
            st.markdown(f"**{config['plot_title']}**", help=config.get('help'))
            render_metric_boxplot(
                df_player_agg,
                metric,
                value_all=data['value_all'],
                value_specific=data['value_specific'],
                left_annotation=config["left_annotation"],
                right_annotation=config["right_annotation"],
                last_n_games=last_n_games
            )

    # Add toggle section for additional visuals based on pre-calculated flag
    if prepared_section_data['has_breakdown']:
        with st.expander(f"Breakdown by game phase"):
            metric_left, metric_right = metrics[0], metrics[1]
            col_left, col_right = st.columns(2)

            # Render additional metrics for the left column
            with col_left:
                for metric, data in prepared_section_data['breakdown_metrics'][metric_left].items():
                    config = data['config']
                    st.markdown(f"**{config['plot_title']}**", help=config.get('help'))
                    render_metric_boxplot(
                        df_player_agg,
                        metric,
                        value_all=data['value_all'],
                        value_specific=data['value_specific'],
                        left_annotation=config["left_annotation"],
                        right_annotation=config["right_annotation"],
                        last_n_games=last_n_games
                    )

            # Render additional metrics for the right column
            with col_right:
                for metric, data in prepared_section_data['breakdown_metrics'][metric_right].items():
                    config = data['config']
                    st.markdown(f"**{config['plot_title']}**", help=config.get('help'))
                    render_metric_boxplot(
                        df_player_agg,
                        metric,
                        value_all=data['value_all'],
                        value_specific=data['value_specific'],
                        left_annotation=config["left_annotation"],
                        right_annotation=config["right_annotation"],
                        last_n_games=last_n_games
                    )