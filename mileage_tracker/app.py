import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State


################################################################################
################################ USER INTERFACE ################################
################################################################################

# Initialize the Flask server
# server = Flask(__name__)
# server.config['SECRET_KEY'] = os.urandom(12)

# Initialize the Dash application
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
# app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.FLATLY])
app.title = 'Dash Planner'

# Set up the layout of the application
app.layout = html.Div(children=[
    # Navbar
    dbc.NavbarSimple(
        # children=[dbc.NavItem(dbc.NavLink("Login", href="#"))],
        children=[
            dbc.NavLink("Logout", href="#", id="open-login", n_clicks=0),
        ],
        brand="Dash Budget",
        brand_href="#",
        color="primary",
        dark=True,
    ),
    # Main portion of the page
    html.Div(children=[
        # html.P('Hello')
        dbc.Col(dbc.Tabs([
            dbc.Tab(dashboard_tab, label="Dashboard"),
            dbc.Tab(expense_tab, label="Expenses"),
            dbc.Tab(deposits_tab, label="Deposits"),
            # dbc.Tab(budgets_tab, label="Budgets"),
            # dbc.Tab(calculator_tab, label="Calculator"),
        ])),
    ], className="mt-4"),
])


# @server.route('/home')
# def home():
#     return app.index()

################################################################################
################################### CALLBACKS ##################################
################################################################################



################################################################################
##################################### END ######################################
################################################################################

if __name__ == '__main__':
    app.run_server(debug=True)
