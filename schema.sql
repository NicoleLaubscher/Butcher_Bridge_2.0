-- ButcherBridge MySQL 8 schema deliverable.
-- Operational deployments should normally apply the equivalent Alembic migration.

CREATE DATABASE IF NOT EXISTS butcherbridge
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE butcherbridge;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(30) NOT NULL DEFAULT 'retailer',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE scenarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  code VARCHAR(60) NOT NULL UNIQUE,
  description TEXT NOT NULL,
  expected_outcome VARCHAR(80) NOT NULL,
  product VARCHAR(120) NOT NULL,
  window_open DATE NOT NULL,
  window_close DATE NOT NULL,
  commitment_deadline DATE NOT NULL,
  compatibility_days INT NOT NULL DEFAULT 3,
  minimum_fill_rate DOUBLE NOT NULL DEFAULT 0.95,
  minimum_on_time_rate DOUBLE NOT NULL DEFAULT 0.95,
  status VARCHAR(30) NOT NULL DEFAULT 'open',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT ck_scenario_compatibility_days CHECK (compatibility_days >= 0),
  CONSTRAINT ck_scenario_fill_rate CHECK (minimum_fill_rate BETWEEN 0 AND 1),
  CONSTRAINT ck_scenario_on_time CHECK (minimum_on_time_rate BETWEEN 0 AND 1),
  INDEX ix_scenarios_code (code),
  INDEX ix_scenarios_product (product)
) ENGINE=InnoDB;

CREATE TABLE retailers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  area VARCHAR(120) NOT NULL,
  contact_email VARCHAR(190),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_retailer_name_area UNIQUE (name, area),
  INDEX ix_retailers_area (area)
) ENGINE=InnoDB;

CREATE TABLE suppliers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL UNIQUE,
  verified BOOLEAN NOT NULL DEFAULT FALSE,
  contact_email VARCHAR(190),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE demands (
  id INT AUTO_INCREMENT PRIMARY KEY,
  scenario_id INT NOT NULL,
  retailer_id INT NOT NULL,
  product VARCHAR(120) NOT NULL,
  quantity_kg DOUBLE NOT NULL,
  required_date DATE NOT NULL,
  submitted_date DATE NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  baseline_price_per_kg DOUBLE NOT NULL,
  baseline_logistics_cost DOUBLE NOT NULL DEFAULT 0,
  baseline_handling_cost DOUBLE NOT NULL DEFAULT 0,
  baseline_distance_km DOUBLE NOT NULL DEFAULT 0,
  baseline_trips DOUBLE NOT NULL DEFAULT 1,
  baseline_fill_rate DOUBLE NOT NULL DEFAULT 1,
  baseline_on_time_rate DOUBLE NOT NULL DEFAULT 1,
  orders_per_month DOUBLE NOT NULL DEFAULT 1,
  individual_procurement_cost DOUBLE NOT NULL DEFAULT 0,
  withdrawn_at DATETIME,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_demand_scenario FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE,
  CONSTRAINT fk_demand_retailer FOREIGN KEY (retailer_id) REFERENCES retailers(id) ON DELETE RESTRICT,
  CONSTRAINT ck_demand_positive_quantity CHECK (quantity_kg > 0),
  CONSTRAINT ck_demand_baseline_price CHECK (baseline_price_per_kg >= 0),
  CONSTRAINT ck_demand_fill_rate CHECK (baseline_fill_rate BETWEEN 0 AND 1),
  CONSTRAINT ck_demand_on_time CHECK (baseline_on_time_rate BETWEEN 0 AND 1),
  INDEX ix_demand_scenario_product_status (scenario_id, product, status)
) ENGINE=InnoDB;

CREATE TABLE supplier_quotes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  scenario_id INT NOT NULL,
  supplier_id INT NOT NULL,
  product VARCHAR(120) NOT NULL,
  capacity_kg DOUBLE NOT NULL,
  lead_time_days INT NOT NULL,
  fixed_fulfilment_cost DOUBLE NOT NULL DEFAULT 0,
  variable_fulfilment_per_kg DOUBLE NOT NULL DEFAULT 0,
  handling_cost DOUBLE NOT NULL DEFAULT 0,
  route_distance_km DOUBLE NOT NULL DEFAULT 0,
  expected_fill_rate DOUBLE NOT NULL DEFAULT 1,
  expected_on_time_rate DOUBLE NOT NULL DEFAULT 1,
  fulfilment_mode VARCHAR(30) NOT NULL DEFAULT 'delivery',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_quote_scenario FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE,
  CONSTRAINT fk_quote_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT,
  CONSTRAINT uq_quote_scenario_supplier_product UNIQUE (scenario_id, supplier_id, product),
  CONSTRAINT ck_quote_capacity CHECK (capacity_kg > 0),
  CONSTRAINT ck_quote_lead_time CHECK (lead_time_days >= 0),
  CONSTRAINT ck_quote_fill_rate CHECK (expected_fill_rate BETWEEN 0 AND 1),
  CONSTRAINT ck_quote_on_time CHECK (expected_on_time_rate BETWEEN 0 AND 1),
  INDEX ix_quote_scenario_product (scenario_id, product)
) ENGINE=InnoDB;

CREATE TABLE price_tiers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  quote_id INT NOT NULL,
  minimum_kg DOUBLE NOT NULL,
  price_per_kg DOUBLE NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_tier_quote FOREIGN KEY (quote_id) REFERENCES supplier_quotes(id) ON DELETE CASCADE,
  CONSTRAINT uq_price_tier_minimum UNIQUE (quote_id, minimum_kg),
  CONSTRAINT ck_tier_minimum CHECK (minimum_kg >= 0),
  CONSTRAINT ck_tier_price CHECK (price_per_kg >= 0)
) ENGINE=InnoDB;

CREATE TABLE supplier_service_areas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  quote_id INT NOT NULL,
  area VARCHAR(120) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_area_quote FOREIGN KEY (quote_id) REFERENCES supplier_quotes(id) ON DELETE CASCADE,
  CONSTRAINT uq_quote_service_area UNIQUE (quote_id, area)
) ENGINE=InnoDB;

CREATE TABLE evaluation_runs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  scenario_id INT NOT NULL,
  run_by_user_id INT,
  decision VARCHAR(60) NOT NULL,
  input_snapshot TEXT NOT NULL,
  result_snapshot TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_run_scenario FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE,
  CONSTRAINT fk_run_user FOREIGN KEY (run_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE fulfilment_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  scenario_id INT NOT NULL,
  supplier_name VARCHAR(160) NOT NULL,
  ordered_quantity_kg DOUBLE NOT NULL,
  delivered_quantity_kg DOUBLE NOT NULL,
  actual_total_cost DOUBLE NOT NULL,
  due_date DATE NOT NULL,
  delivered_date DATE NOT NULL,
  actual_logistics_cost DOUBLE NOT NULL DEFAULT 0,
  actual_trips INT NOT NULL DEFAULT 1,
  actual_distance_km DOUBLE NOT NULL DEFAULT 0,
  exception_notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_fulfilment_scenario FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE,
  CONSTRAINT ck_fulfilment_ordered_quantity CHECK (ordered_quantity_kg > 0),
  CONSTRAINT ck_fulfilment_delivered_quantity CHECK (delivered_quantity_kg >= 0)
) ENGINE=InnoDB;

