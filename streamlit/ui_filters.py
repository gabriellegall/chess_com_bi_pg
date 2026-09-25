import pandas as pd
import streamlit as st


def render_sidebar_filters(dependent_data: pd.DataFrame, filter_fields: list) -> dict:
    """
    Renders sidebar filters in order. Each categorical selection narrows `current_data`,
    so later filters (and slider defaults) are scoped to prior selections.
    Field order in `filter_fields` therefore matters.
    """
    st.sidebar.header("Game Filters")
    selections = {}
    current_data = dependent_data.copy()

    for field in filter_fields:
        if field == "playing_rating_range":
            ratings = pd.concat([
                current_data["playing_rating"].dropna(),
                current_data["opponent_rating"].dropna(),
            ])

            if ratings.empty:
                default_min, default_max = 100, 2000
            else:
                default_min = max(100, int(ratings.min()))
                default_max = min(2000, int(ratings.max()))

            rating_min, rating_max = st.sidebar.slider(
                "Rating Range (applies to both playing and opponent rating)",
                min_value=100,
                max_value=2000,
                value=(default_min, default_max),
                step=10,
            )

            selections[field] = (rating_min, rating_max)
            continue

        options = sorted(current_data[field].dropna().unique())

        if not options:
            st.sidebar.warning(f"No '{field.replace('_', ' ')}' options available.")
            selections[field] = None
            continue

        selections[field] = st.sidebar.selectbox(
            field.replace("_", " ").title(),
            options=options,
            key=f"sidebar_{field}",
        )

        current_data = current_data[current_data[field] == selections[field]]

    return selections


def render_page_filters(
    dependent_data: pd.DataFrame,
    filter_fields: list,
    context: str,
    *,
    style: str = "radio",
    horizontal: bool = True,
    add_all: bool = False,
) -> dict:
    """
    Creates select boxes in the main content area for each field in `filter_fields`, arranging them in columns.
    Only shows the values relevant based on the `dependent_data`.
    Returns the user's selections as a dictionary.
    """
    selections = {}
    cols = st.columns(len(filter_fields))

    for col, field in zip(cols, filter_fields):
        with col:
            raw_options = sorted(list(dependent_data[field].dropna().unique()))
            if not raw_options:
                st.warning(f"No '{field.replace('_', ' ')}' options.")
                continue

            options = ["All"] + raw_options if add_all else raw_options
            label = field.replace("_", " ").title()
            key = f"{context}_{field}"

            if style == "dropdown":
                selections[field] = st.selectbox(label, options, key=key, index=0)
            else:
                selections[field] = st.radio(
                    label,
                    options,
                    horizontal=horizontal,
                    label_visibility="collapsed" if horizontal else "visible",
                    key=key,
                    index=0,
                )

    return selections


def apply_filters(df: pd.DataFrame, selections: dict) -> pd.DataFrame:
    """
    Apply sidebar/all selections to the given dataframe.
    Handles both rating range tuples and categorical filters.
    """
    df_filtered = df.copy()
    for field, value in selections.items():
        if isinstance(value, tuple):
            min_val, max_val = value
            df_filtered = df_filtered[
                df_filtered["playing_rating"].between(min_val, max_val)
                & df_filtered["opponent_rating"].between(min_val, max_val)
            ]
        elif value and value != "All":
            df_filtered = df_filtered[df_filtered[field] == value]
    return df_filtered