# set the working directory
cd /home/datecounter/Iris || exit 1

# get latest version of the code
git pull

# Roboflow Date Detection ML model API key
export ROBOFLOW_API_KEY="hxbzFhYTazhWI6FQmkhM"

# Launch date counter application
python3 main.py
