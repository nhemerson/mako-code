Pydantic Run:
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