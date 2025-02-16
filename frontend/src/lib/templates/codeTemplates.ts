export const codeTemplates = {
    polars: `# https://docs.pola.rs/api/python/stable/reference/

import polars as pl

data = {"a": [1, 2], "b": [3, 4]}
df = pl.DataFrame(data)
print(df)`,

    sql: `@sql
--https://docs.pola.rs/api/python/stable/reference/sql/index.html

SELECT 
* 
FROM my_table
--save_as:

`,

    bokeh: `# https://docs.bokeh.org/en/latest/docs/user_guide.html

from bokeh.plotting import figure, show

fruits = ['Apples', 'Pears', 'Nectarines', 'Plums', 'Grapes', 'Strawberries']
counts = [5, 3, 4, 2, 4, 6]

p = figure(x_range=fruits, height=350, title="Fruit Counts",
           toolbar_location=None, tools="")

p.vbar(x=fruits, top=counts, width=0.9)

p.xgrid.grid_line_color = None
p.y_range.start = 0

show(p)
`
}; 