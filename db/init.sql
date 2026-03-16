CREATE TABLE ws_config (
  id INT AUTO_INCREMENT PRIMARY KEY,
  base_url VARCHAR(255),
  type VARCHAR(100)
);

CREATE TABLE ws_req_param_details (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tran_id INT,
  tran_type VARCHAR(100),
  req_params TEXT,
  queue_in VARCHAR(100),
  queue_out VARCHAR(100),
  req_params_length INT NULL,
  queue_type VARCHAR(50),
  host_id INT NULL,
  from_ip VARCHAR(50),
  enclosing_tag VARCHAR(50) NULL,
  reserval_api VARCHAR(50) NULL,
  response_type VARCHAR(50) NULL
);

CREATE TABLE ws_req_param_map (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tran_id INT,
  param_name VARCHAR(100),
  param_priority INT,
  is_mandatory CHAR(1),
  is_compress TINYINT,
  regex VARCHAR(255) NULL,
  max_length INT NULL,
  append_length INT NULL,
  value TEXT NULL,
  log_column VARCHAR(100) NULL,
  is_escape TINYINT,
  function_name VARCHAR(100) NULL,
  is_max_length_lp TINYINT
);

CREATE TABLE ws_endpoint_config (
  id INT AUTO_INCREMENT PRIMARY KEY,
  data_template TEXT,
  endpoint_template VARCHAR(255),
  fields TEXT,
  request_format VARCHAR(50),
  response_include_paths TEXT,
  response_format VARCHAR(50),
  response_code_paths VARCHAR(255),
  type VARCHAR(100),
  config_id INT,
  request_headers TEXT,
  guaranteed TINYINT,
  token_configuration_id INT NULL,
  token_request_id INT NULL,
  reversal_type VARCHAR(100) NULL,
  variable_fields TEXT NULL,
  connection_timeout INT,
  read_timeout INT,
  method VARCHAR(10),
  ex_req_res_log TEXT NULL
);


