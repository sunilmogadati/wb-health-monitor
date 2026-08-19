{# Use the custom +schema name literally (warehouse, published) instead of dbt's default
   "<target_schema>_<custom>" prefixing, so the zones land in clean, predictable schemas. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
