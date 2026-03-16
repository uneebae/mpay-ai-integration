# Database Schema Reference

The Mpay integration agent manages four tables that configure how Mpay connects
to external APIs.

## Tables overview

| Table                  | Purpose                                                 |
| ---------------------- | ------------------------------------------------------- |
| `ws_config`            | Base URL and type of each API service                   |
| `ws_req_param_details` | Transaction-level request configuration                 |
| `ws_req_param_map`     | Individual parameter definitions for each transaction   |
| `ws_endpoint_config`   | Endpoint-specific config (templates, formats, timeouts) |

## `ws_config`

The top-level service registration. One row per external API.

| Column     | Type         | Nullable | Notes                          |
| ---------- | ------------ | -------- | ------------------------------ |
| `id`       | INT          | No       | AUTO_INCREMENT, PRIMARY KEY    |
| `base_url` | VARCHAR(255) | Yes      | e.g. `https://api.example.com` |
| `type`     | VARCHAR(100) | Yes      | Service type identifier        |

## `ws_req_param_details`

Defines the transaction type and its request parameter list.

| Column              | Type         | Nullable | Notes                                   |
| ------------------- | ------------ | -------- | --------------------------------------- |
| `id`                | INT          | No       | AUTO_INCREMENT, PK                      |
| `tran_id`           | INT          | Yes      | Transaction identifier (start from 100) |
| `tran_type`         | VARCHAR(100) | Yes      | e.g. `PAYMENT`, `INQUIRY`               |
| `req_params`        | TEXT         | Yes      | Comma-separated param names             |
| `queue_in`          | VARCHAR(100) | Yes      | Inbound queue name                      |
| `queue_out`         | VARCHAR(100) | Yes      | Outbound queue name                     |
| `req_params_length` | INT          | Yes      | Number of parameters                    |
| `queue_type`        | VARCHAR(50)  | Yes      | Queue type                              |
| `host_id`           | INT          | Yes      | Host identifier                         |
| `from_ip`           | VARCHAR(50)  | Yes      | Source IP restriction                   |
| `enclosing_tag`     | VARCHAR(50)  | Yes      | XML enclosing tag                       |
| `reserval_api`      | VARCHAR(50)  | Yes      | Reversal API reference                  |
| `response_type`     | VARCHAR(50)  | Yes      | e.g. `JSON`, `XML`                      |

## `ws_req_param_map`

One row per parameter per transaction. Defines validation rules and ordering.

| Column             | Type         | Nullable | Notes                                   |
| ------------------ | ------------ | -------- | --------------------------------------- |
| `id`               | INT          | No       | AUTO_INCREMENT, PK                      |
| `tran_id`          | INT          | Yes      | Links to `ws_req_param_details.tran_id` |
| `param_name`       | VARCHAR(100) | Yes      | Parameter name                          |
| `param_priority`   | INT          | Yes      | Order in the request                    |
| `is_mandatory`     | CHAR(1)      | Yes      | `Y` or `N`                              |
| `is_compress`      | TINYINT      | Yes      | 1 = compress value                      |
| `regex`            | VARCHAR(255) | Yes      | Validation regex                        |
| `max_length`       | INT          | Yes      | Max parameter length                    |
| `append_length`    | INT          | Yes      | Padding length                          |
| `value`            | TEXT         | Yes      | Default/fixed value                     |
| `log_column`       | VARCHAR(100) | Yes      | Column for logging                      |
| `is_escape`        | TINYINT      | Yes      | 1 = escape special chars                |
| `function_name`    | VARCHAR(100) | Yes      | Transform function                      |
| `is_max_length_lp` | TINYINT      | Yes      | Left-pad to max length                  |

## `ws_endpoint_config`

Endpoint-level configuration: templates, formats, timeouts.

| Column                   | Type         | Nullable | Notes                         |
| ------------------------ | ------------ | -------- | ----------------------------- |
| `id`                     | INT          | No       | AUTO_INCREMENT, PK            |
| `data_template`          | TEXT         | Yes      | Request body template         |
| `endpoint_template`      | VARCHAR(255) | Yes      | URL path template             |
| `fields`                 | TEXT         | Yes      | Comma-separated field list    |
| `request_format`         | VARCHAR(50)  | Yes      | `JSON_POST`, `XML`, `FORM`    |
| `response_include_paths` | TEXT         | Yes      | JSONPath for response parsing |
| `response_format`        | VARCHAR(50)  | Yes      | `JSON`, `XML`                 |
| `response_code_paths`    | VARCHAR(255) | Yes      | Path to response code         |
| `type`                   | VARCHAR(100) | Yes      | Transaction type              |
| `config_id`              | INT          | Yes      | Links to `ws_config.id`       |
| `request_headers`        | TEXT         | Yes      | Custom headers (JSON)         |
| `guaranteed`             | TINYINT      | Yes      | 1 = guaranteed delivery       |
| `token_configuration_id` | INT          | Yes      | OAuth token config ID         |
| `token_request_id`       | INT          | Yes      | OAuth token request ID        |
| `reversal_type`          | VARCHAR(100) | Yes      | Reversal handling type        |
| `variable_fields`        | TEXT         | Yes      | Dynamic field definitions     |
| `connection_timeout`     | INT          | Yes      | Connect timeout (ms)          |
| `read_timeout`           | INT          | Yes      | Read timeout (ms)             |
| `method`                 | VARCHAR(10)  | Yes      | HTTP method                   |
| `ex_req_res_log`         | TEXT         | Yes      | Extended logging config       |

## Entity relationships

```
ws_config (1) ◄──── (N) ws_endpoint_config
                              │
                              │ type / tran_type
                              │
ws_req_param_details (1) ◄──── linked by tran_id ────► (N) ws_req_param_map
```

- `ws_endpoint_config.config_id` → `ws_config.id`
- `ws_req_param_map.tran_id` → `ws_req_param_details.tran_id`
- `ws_endpoint_config.type` typically matches `ws_req_param_details.tran_type`
