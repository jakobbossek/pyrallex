# build
# The next step is to generate distribution packages for the package.
# These are archives that are uploaded to the Python Package Index and can be installed by pip.
python -m pip install --upgrade build

# Now run this command from the same directory where pyproject.toml is located:
python -m build

python -m pip install --upgrade twine

# real upload to pypi
python -m twine upload dist/*
python -m pip install pyrallex


