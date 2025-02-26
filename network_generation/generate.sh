#!/bin/bash
# generated with help of Gemini (fantavit)

CONFIG_FILE="generation_config.toml"

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
done < generation_config.toml

echo "Printing the loaded configuration..."
for key in "${!config[@]}"; do
    echo "  $key: ${config[$key]}"
done

# Generate network
netgenerate \
    --grid \
    --grid.number=${config[network,grid_size]} \
    --grid.length=${config[network,edge_length]} \
    --j=${config[network,intersection_control]} \
    --no-turnarounds=${config[network,no_turnarounds]} \
    --grid.attach-length=${config[network,terminus_length]} \
    --sidewalks.guess=${config[network,sidewalks]} \
    --output-file=${config[network,output_file]} 

# Generate bus stops
python generate_bus_routes.py \
    --net_file=${config[network,output_file]} \
    --bus_stop_file=${config[bus_stops,output_file]} \
    --every_nth=${config[bus_stops,every_nth]} \
    --stop_duration=${config[routes,stop_duration]} \
    --stop_position=${config[bus_stops,stop_position]} \
    --num_buses=${config[routes,num_buses]} \
    --route_repeats=${config[routes,repeat]} \
    --route_file=${config[routes,output_file]} \
    --sumocfg_file=${config[sumocfg,output_file]}