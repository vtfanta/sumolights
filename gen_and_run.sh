#!/usr/bin/env bash

CONFIG_FILE="network_generation/generation_config.toml"

# Declare an associative array
declare -A config

# Read the entire TOML file into the associative array
while IFS= read -r line; do
  if [[ "$line" =~ ^\[.*\]$ ]]; then # Check for table headers (e.g., [database])
    current_table="${line:1:-1}" # Extract table name
  elif [[ "$line" =~ ^[^#].*=.+$ ]]; then # Check for key-value pairs (not comments)
    key=$(echo "$line" | cut -d '=' -f 1 | tr -d ' ')  # Extract key, remove spaces
    value=$(echo "$line" | cut -d '=' -f 2- | tr -d ' ') # Extract value, remove spaces

    # Handle nested tables (create nested associative arrays if needed)
    if [[ -n "$current_table" ]]; then
        eval "config[\"$current_table\",\"$key\"]=\"$value\""
    else
        config["$key"]="$value"
    fi
  fi
done < $CONFIG_FILE

./network_generation/generate.sh $CONFIG_FILE

python run.py -sim ${config[sumocfg,output_file]} -demand custom -n 1 -tsc maxpressure -mode test -gmin 5 