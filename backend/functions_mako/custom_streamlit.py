import streamlit as st
import toml
import json

##### streamlit utilities #####

def setup_page():

    #push to prod
    st.set_page_config(
        # page_icon='ff.png',
        layout='wide',
        initial_sidebar_state="collapsed",
        page_title="Mako BI"
    )

def update_config_toml(title_1:str, title_2:str, new_value:str) -> None:
    try:
        #path to config file
        config_path = './.streamlit/config.toml'
        #load toml to update
        with open('config.toml') as f:
            config_data = toml.load(f)
        #update the config data
        config_data[title_1][title_2] = new_value
        #write the updated data back to the config file
        with open(config_path, 'w') as f:    
            toml.dump(config_data, f)
    except Exception as e:
        st.error(f"Failed to update the config TOML file: {e}")

# Function to load and update the TOML file
def update_secrets_toml(new_secret: str) -> None:
    try:
        # Load existing secrets TOML
        with open('./.streamlit/.secrets.toml', 'r') as file:
            secrets_data = toml.load(file)
            print(secrets_data)

        # Update the secrets data with the new Google service account
        secrets_data['google_service_account'] = json.loads(new_secret)
        print(secrets_data)

        # Write the updated TOML back to the file
        with open('.secrets.toml', 'w') as file:
            toml.dump(secrets_data, file)

        st.success("Successfully updated the secrets TOML file.")
    except Exception as e:
        st.error(f"Failed to update the secrets TOML file: {e}")

### Custom IDE Elements

custom_btns = [{
"name": "Ctrl+Enter or Push to Run Code",
"feather": "Play",
"primary": True,
"hasText": True,
"showWithIcon": True,
"alwaysOn": True,
"commands": ["submit",["infoMessage", 
                    {
                     "text":"Code Ran, Now press Test Code Button",
                     "timeout": 3000, 
                     "classToggle": "show"
                    }
                   ]
               ],
"style": {"bottom": "0.44rem", "right": "0.4rem"},
},
{
"name": "Command",
"feather": "Terminal",
"primary": True,
"hasText": True,
"commands": ["openCommandPallete"],
"style": {"bottom": "3.5rem", "right": "0.4rem"}
}
]

# css to inject related to info bar
css_string = '''
background-color: #bee1e5;

body > #root .ace-streamlit-dark~& {
   background-color: #262830;
}

.ace-streamlit-dark~& span {
   color: #fff;
   opacity: 0.6;
}

span {
   color: #000;
   opacity: 0.5;
}

.code_editor-info.message {
   width: inherit;
   margin-right: 75px;
   order: 2;
   text-align: center;
   opacity: 0;
   transition: opacity 0.7s ease-out;
}

.code_editor-info.message.show {
   opacity: 0.6;
}

.ace-streamlit-dark~& .code_editor-info.message.show {
   opacity: 0.5;
}
'''
# create info bar dictionary
info_bar = {
  "name": "language info",
  "css": css_string,
  "style": {
            "order": "1",
            "display": "flex",
            "flexDirection": "row",
            "alignItems": "center",
            "width": "100%",
            "height": "2.5rem",
            "padding": "0rem 0.75rem",
            "borderRadius": "8px 8px 0px 0px",
            "zIndex": "9993"
           },
  "info": [{
            "name": "python",
            "style": {"width": "100px"}
           }]
}

