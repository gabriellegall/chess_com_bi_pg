{% macro games_scope_condition(alias='') -%}
{%- set prefix = alias ~ '.' if alias else '' -%}
{{ prefix }}end_time >= date_trunc('month', current_date - interval '{{ var('data_scope')['month_history_depth'] }} months') and {{ prefix }}time_class = any(array{{ var('data_scope')['time_class'] }}::text[]) and {{ prefix }}rated
{%- endmacro %}