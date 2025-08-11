import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import yaml
from pathlib import Path
from config import get_plot_config, get_section_config
from data_processing import get_raw_data, get_players_aggregates, get_player_metric_values, get_summary_kpis, calculate_win_loss_draw

st.set_page_config(layout="wide")

@st.cache_data
def load_dbt_project_config():
    """Loads the dbt_project.yml file."""
    # The CWD is the 'streamlit' folder, so we go up one level to the project root.
    project_root = Path.cwd().parent
    config_path = project_root / "dbt" / "dbt_project.yml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def render_sidebar_filters(dependent_data: pd.DataFrame, filter_fields: list) -> dict:
    """
    Creates select boxes in the sidebar for each field in `filter_fields`.
    Only shows the values relevant based on the `dependent_data`.
    Returns the user's selections as a dictionary.
    """
    st.sidebar.header("Game Filters")
    selections = {}
    for field in filter_fields:
        options = sorted(list(dependent_data[field].unique()))
        if not options:
            st.sidebar.warning(f"No '{field.replace('_', ' ')}' options.")
            continue
        
        selected_option = st.sidebar.selectbox(
            f"Select {field.replace('_', ' ').title()}",
            options=options
        )
        selections[field] = selected_option
    return selections

def render_main_filters(dependent_data: pd.DataFrame, filter_fields: list) -> dict:
    """
    Creates select boxes in the main content area for each field in `filter_fields`, arranging them in columns.
    Only shows the values relevant based on the `dependent_data`.
    Returns the user's selections as a dictionary.
    """
    selections = {}
    
    # Create a number of columns equal to the number of filters
    cols = st.columns(len(filter_fields))
    
    # Iterate over the columns and fields simultaneously
    for col, field in zip(cols, filter_fields):
        with col:
            options = sorted(list(dependent_data[field].unique()))
            if not options:
                st.warning(f"No '{field.replace('_', ' ')}' options.")
                continue
            
            selected_option = st.radio(
                f"Select {field.replace('_', ' ').title()}",
                options=options,
                horizontal=True,
                label_visibility="collapsed" # Hides the label above the radio buttons
            )
            selections[field] = selected_option
    return selections

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

def render_summary_header(kpis: dict, last_n_games: int):
    """
    Renders a summary header with KPIs for White and Black from pre-calculated data.
    Displays the `last_n_games` information in the titles.
    """
    col1, col2 = st.columns(2)

    for color, data in kpis.items():
        if color not in ['White', 'Black']:
            continue

        container = col1 if color == 'White' else col2
        with container:
            emoji = "⚪" if color == "White" else "⚫"
            st.subheader(f"{emoji} Playing as {color}")
            
            if data is None:
                st.info(f"No games played as {color} with current filters.")
                continue

            # Overall stats row
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                st.markdown(f"<span style='color: yellow; font-size: 20px; font-weight: bold;'>|</span> Overall Games", unsafe_allow_html=True)
                st.metric("Total Games", f"{data['total_games']}")
            with sub_col2:
                st.markdown(f"<span style='color: yellow; font-size: 20px; font-weight: bold;'>|</span> Overall Win Rate", unsafe_allow_html=True)
                st.metric(
                    "Overall Win Rate",
                    value=f"{data['win_rate_overall']:.0f}%"
                )

            st.markdown("---")

            # Recent stats row
            sub_col3, sub_col4 = st.columns(2)
            with sub_col3:
                st.markdown(f"<span style='color: yellow;'>★</span> Recent Games (Last {last_n_games})", unsafe_allow_html=True)
                st.metric("Recent Games", f"{data['total_recent_games']}")
            with sub_col4:
                st.markdown(f"<span style='color: yellow;'>★</span> Recent Win Rate", unsafe_allow_html=True)
                st.metric(
                    "Recent Win Rate",
                    value=f"{data['win_rate_recent']:.0f}%",
                    delta=f"{data['delta_vs_overall']:.1f} pts vs overall",
                )

    # Add a checkbox at the bottom to show the raw data for recent games
    if st.checkbox(f"Show data for last {last_n_games} games"):
        st.dataframe(kpis['recent_games_df'], use_container_width=True)

### --- Main Application ---

# Load initial data
raw_data                    = get_raw_data()
dbt_config                  = load_dbt_project_config()
dbt_game_phases_config      = dbt_config.get("vars", {}).get("game_phases", {})
dbt_score_thresholds_config = dbt_config.get("vars", {}).get("score_thresholds", {})
plot_config                 = get_plot_config(dbt_game_phases_config, dbt_score_thresholds_config)
section_config              = get_section_config(dbt_game_phases_config, dbt_score_thresholds_config)

st.title("Chess.com Player Performance Benchmark")

### --- Sidebar selection ---
all_usernames = sorted(raw_data["username"].unique())
default_user = "Zundorn" if "Zundorn" in all_usernames else all_usernames[0]

selected_username = st.sidebar.selectbox(
    "Select a Player to Analyze",
    options=all_usernames,
    index=all_usernames.index(st.session_state.get("selected_username", default_user)),
    key="selected_username"
)

last_n_games = st.sidebar.slider(
    "Number of recent games to analyze",
    min_value=10,
    max_value=60,
    value=30,
    step=1,
    key="last_n_games"
)

### --- Dependent filters ---
user_specific_data = raw_data[raw_data['username'] == selected_username]

# Define filter fields for each section 
fields_sidebar_filter = ["time_control", "playing_rating_range"]
fields_main_filter = ["playing_as", "playing_result"]

# Render and get sidebar filters
sidebar_selections = render_sidebar_filters(user_specific_data, fields_sidebar_filter)

### --- Summary KPIs header --- 

# Apply filters and render the summary header
df_sidebar_filtered = user_specific_data.copy()
for field, value in sidebar_selections.items():
    if value:
        df_sidebar_filtered = df_sidebar_filtered[df_sidebar_filtered[field] == value]

if df_sidebar_filtered.empty:
    st.warning("No data available for the selected filters.")
else:
    with st.container(border=True):
        st.header(f"How is {selected_username} performing?")
        df_sidebar_filtered = calculate_win_loss_draw(df_sidebar_filtered)
        summary_kpis = get_summary_kpis(df_sidebar_filtered, selected_username, last_n_games)
        render_summary_header(summary_kpis, last_n_games)

### --- Benchmark --- 
with st.container(border=True):
    st.header(f"How does {selected_username} compare to other similar players?")
    
    # Render and get main page filters
    main_selections = render_main_filters(user_specific_data, fields_main_filter)

    # Combine all selections into a single dictionary
    all_selections = {**sidebar_selections, **main_selections}

    # Apply the combined filters to the entire dataset
    df_filtered = raw_data.copy()
    for field, value in all_selections.items():
        if value: # Ensure a selection was made
            df_filtered = df_filtered[df_filtered[field] == value]

    # Get the aggregated data for all players
    df_player_agg = get_players_aggregates(df_filtered, plot_config)

    # Add explanatory context text based on the filter selection 
    st.markdown(f"""
    In this section, we compare the performance of **{selected_username}** with other similar players (n={len(df_player_agg)}), holding constant: 
    - Color played: **{main_selections.get('playing_as', 'N/A')}**
    - Playing result: **{main_selections.get('playing_result', 'N/A')}**
    - Time control: **{sidebar_selections.get('time_control', 'N/A')}**
    - Rating range: **{sidebar_selections.get('playing_rating_range', 'N/A')}**
    """)

    # Render plots for each section
    if df_player_agg.empty:
        st.warning("No player data available for the selected filters. Please adjust your selections.")
    else:
        username_to_highlight = selected_username
        if username_to_highlight not in df_player_agg['username'].unique():
            st.warning(f"'{username_to_highlight}' has fewer than 30 games for the selected filters and cannot be benchmarked. Please adjust the filters or select another player.")
        else:
            # Render the legend
            render_legend(username=username_to_highlight, last_n_games=last_n_games)

            # Import the data for each section and each plot
            all_section_plot_data = prepare_section_plot_data(
                section_config, plot_config, df_filtered, username_to_highlight, last_n_games
            )

            # For each section, render the plots
            for prepared_section_data in all_section_plot_data:
                with st.container(border=True):
                    render_plot_section(prepared_section_data, df_player_agg, last_n_games)
