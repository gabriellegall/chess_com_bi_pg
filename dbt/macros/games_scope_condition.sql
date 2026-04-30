{% macro games_scope_condition(alias='') -%}
{%- set prefix = alias ~ '.' if alias else '' -%}
    {{ prefix }}end_time >= DATE_TRUNC('MONTH', CURRENT_DATE - INTERVAL '{{ var('data_scope')['month_history_depth'] }} MONTHS') 
    AND {{ prefix }}time_class = ANY(ARRAY{{ var('data_scope')['time_class'] }}::text[]) 
    AND {{ prefix }}rated
{%- endmacro %}