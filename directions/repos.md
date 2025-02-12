### Pydantic Run:
website: https://pydantic.run
https://github.com/pydantic/pydantic.run

README.md: https://github.com/pydantic/pydantic.run/blob/main/README.md

pydantic.run
Python browser sandbox based on Pyodide. Write and share Python code, run it in the browser.

Built to demonstrate Pydantic, PydanticAI, and Pydantic Logfire.

If you choose to save code, it's stored in CloudFlare's R2 object storage, and should be available for one year.

Dependencies
Dependencies are installed when code is run.

Dependencies can be either:

defined via inline script metadata — e.g. a comment at the top of the file, as used by uv
or, inferred from imports in the code — e.g. import pydantic will install the pydantic package
Sandbox via link

To programmatically create a sandbox, make a GET request to https://pydantic.run/new, with the files parameter set to a JSON object containing the files you want to show.

The response is a 302 redirect to the newly created sandbox, hence you can direct a user to a sandbox with the code you want them to see. Repeated requests with the same files will use the same sandbox.

files should be an array of objects with the following keys:

name - (string) the name of the file
content - (string) the content of the file
Optionally activeIndex - (integer) indicating which file/tab is open by default, the highest value wins
You can also set the tab parameter to select which tab is open by default, that advantage of using this over activeIndex is that it will reuse the same sandbox for requests choosing different tabs.

Here's a minimal HTML page that provides a link to create a new sandbox with two files:

<div>loading...</div>
<script>
  const files = [
    {
      name: 'main.py',
      content: 'print("This is an example!")',
      activeIndex: 1,
    },
    {
      name: 'another.py',
      content: 'x = 42\nprint(f"The answer is {x}")',
    },
  ]
  const redirectUrl = new URL('https://pydantic.run/new')
  redirectUrl.searchParams.append('files', JSON.stringify(files))
  document.querySelector('div').innerHTML = `<a href="${redirectUrl}">Click here to create a new sandbox</a>`
</script>


### Streamlit:
https://github.com/streamlit/streamlit

- Dataframe Component:
  https://github.com/streamlit/streamlit/blob/develop/frontend/lib/src/components/widgets/DataFrame/DataFrame.tsx


### Duck UI
https://github.com/caioricciuti/duck-ui

- SQL Editor: https://github.com/caioricciuti/duck-ui/blob/main/src/components/editor/SqlEditor.tsx
- Data Table: https://github.com/caioricciuti/duck-ui/blob/main/src/components/table/DuckUItable.tsx

### Polars documentation:

Global SQL

Querying
SQL queries can be issued against compatible data structures in the current globals, against specific frames, or incorporated into expressions.

Global SQL
Both SQLContext and the polars.sql() function can be used to execute SQL queries mediated by the Polars execution engine against Polars DataFrame, LazyFrame, and Series data, as well as Pandas DataFrame and Series, and PyArrow Table and RecordBatch objects. Non-Polars objects are implicitly converted to DataFrame when used in a SQL query; for PyArrow, and Pandas data that uses PyArrow dtypes, this conversion can often be zero-copy if the underlying data maps cleanly to a natively-supported dtype.

Example:

import polars as pl
import pandas as pd

polars_df = pl.DataFrame({"a": [1, 2, 3, 4], "b": [4, 5, 6, 7]})
pandas_df = pd.DataFrame({"a": [3, 4, 5, 6], "b": [6, 7, 8, 9]})
polars_series = (polars_df["a"] * 2).rename("c")
pyarrow_table = polars_df.to_arrow()

pl.sql(
    """
    SELECT a, b, SUM(c) AS c_total FROM (
      SELECT * FROM polars_df                  -- polars frame
        UNION ALL SELECT * FROM pandas_df      -- pandas frame
        UNION ALL SELECT * FROM pyarrow_table  -- pyarrow table
    ) all_data
    INNER JOIN polars_series
      ON polars_series.c = all_data.b          -- polars series
    GROUP BY "a", "b"
    ORDER BY "a", "b"
    """
).collect()

# shape: (3, 3)
# ┌─────┬─────┬─────────┐
# │ a   ┆ b   ┆ c_total │
# │ --- ┆ --- ┆ ---     │
# │ i64 ┆ i64 ┆ i64     │
# ╞═════╪═════╪═════════╡
# │ 1   ┆ 4   ┆ 8       │
# │ 3   ┆ 6   ┆ 18      │
# │ 5   ┆ 8   ┆ 8       │
# └─────┴─────┴─────────┘