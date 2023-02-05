# This is a simple web server for a traffic counting application.
# It's your job to extend it by adding the backend functionality to support
# recording the traffic in a SQL database. You will also need to support
# some predefined users and access/session control. You should only
# need to extend this file. The client side code (html, javascript and css)
# is complete and does not require editing or detailed understanding.

# import the various libraries needed
import http.cookies as Cookie  # some cookie handling support
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)  # the heavy lifting of the web server
import urllib  # some url parsing support
import json  # support for json encoding
import sys  # needed for agument handling
import sqlite3
import string
import random
import time
import datetime as dt
from datetime import datetime


def access_database(query):
    connect = sqlite3.connect("traffic.db")
    cursor = connect.cursor()
    cursor.execute(query)
    connect.commit()
    connect.close()


# access_database requires the name of an sqlite3 database file and the query.
# It returns the result of the query
def access_database_with_result(query):
    connect = sqlite3.connect("traffic.db")
    cursor = connect.cursor()
    rows = cursor.execute(query).fetchall()
    connect.commit()
    connect.close()
    return rows


def tokenise(size=12, chars=string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def get_sec(time_str):
    """Get Seconds from time."""
    h, m, s = time_str.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def build_response_refill(where, what):
    """This function builds a refill action that allows part of the
    currently loaded page to be replaced."""
    return {"type": "refill", "where": where, "what": what}


### LOGIN LOGOUT - session
def build_response_redirect(where):
    """This function builds the page redirection action
    It indicates which page the client should fetch.
    If this action is used, only one instance of it should
    contained in the response and there should be no refill action."""
    return {"type": "redirect", "where": where}


def handle_validate(iuser, imagic):
    """Decide if the combination of user and magic is valid"""
    ## alter as required
    #### check with database
    # query = access_database_with_result("SELECT users.username, session.magic FROM session \
    #                                      INNER JOIN users ON session.userid = users.userid \
    #                                      WHERE users.username = '{}' AND session.magic = '{}' AND session.end = 0"
    #                                      .format(iuser, imagic))
    # query = access_database_with_result("SELECT * FROM session WHERE userid = '{}' AND magic = '{}'".format(iuser, imagic))
    query = access_database_with_result("SELECT * FROM session WHERE end = 0")
    if len(query) > 0:
        return True
    else:
        return False


def handle_delete_session(iuser, imagic):
    """Remove the combination of user and magic from the data base, ending the login"""
    #### put the login time in database
    #### Automatically logout when the second user login
    response = []
    # query = access_database_with_result("SELECT users.userid, session.magic FROM session \
    #                                      INNER JOIN users ON session.userid = users.userid \
    #                                      WHERE users.username = '{}' AND session.magic = '{}' AND session.end = 0"
    #                                      .format(iuser, imagic))
    # #now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(float(time.time())))
    # now = int(time.time())
    # userid = query[0][0]
    # access_database("UPDATE session SET end = {} WHERE userid = {} AND end=0".format(now, userid))
    parameter = 0
    handle_logout_request(iuser, imagic, parameter)
    response.append(build_response_redirect("/index.html"))
    user = "!"
    magic = ""
    return [user, magic, response]


def handle_login_request(iuser, imagic, parameters):
    """A user has supplied a username (parameters['usernameinput'][0])
    and password (parameters['passwordinput'][0]) check if these are
    valid and if so, create a suitable session record in the database
    with a random magic identifier that is returned.
    Return the username, magic identifier and the response action set."""
    response = []
    if handle_validate(iuser, imagic) == True:
        # the user is already logged in, so end the existing session.
        #### end time to update the session table
        #### I have to create a magic
        #### tokenise for python = magic
        handle_delete_session(iuser, imagic)
    user = ""
    magic = ""
    if (
        "usernameinput" not in parameters.keys()
        or "passwordinput" not in parameters.keys()
    ):
        response.append(
            build_response_refill(
                "message", "Please enter a valid username or password"
            )
        )
        return [user, magic, response]

    query = access_database_with_result(
        "SELECT userid, username FROM users \
                                         WHERE username = '{}' AND password = '{}'".format(
            (parameters["usernameinput"][0]), (parameters["passwordinput"][0])
        )
    )

    ## alter as required
    if len(query) > 0:  ## The user is valid
        query_logged_in = access_database_with_result(
            "SELECT magic FROM session WHERE userid = {}".format(query[0][0])
        )
        token = 0
        if len(query_logged_in) > 0:
            token = query_logged_in[0][0]

        if handle_validate(query[0][1], token) == True:
            handle_delete_session(query[0][1], token)

        userid = query[0][0]
        user = query[0][1]
        magic = tokenise()
        start = int(time.time())
        end = 0

        access_database(
            "INSERT INTO session (userid, magic, start, end) VALUES ({}, '{}', {}, {})".format(
                userid, magic, start, end
            )
        )

        response.append(build_response_redirect("/page.html"))
    else:  ## The user is not valid
        response.append(build_response_refill("message", "Invalid password"))
        user = "!"
        magic = ""
    return [user, magic, response]


def handle_logout_request(iuser, imagic, parameters):
    """This code handles the selection of the logout button on the summary page (summary.html)
    You will need to ensure the end of the session is recorded in the database
    And that the session magic is revoked."""
    response = []
    ## alter as required
    now = int(time.time())
    access_database(
        "UPDATE session SET end = {} WHERE magic = '{}' AND end = 0".format(now, imagic)
    )
    response.append(build_response_redirect("/index.html"))
    user = "!"
    magic = ""
    return [user, magic, response]


### ADDING DATA - traffic
def handle_add_request(iuser, imagic, parameters):
    """The user has requested a vehicle be added to the count
    parameters['locationinput'][0] the location to be recorded
    parameters['occupancyinput'][0] the occupant count to be recorded
    parameters['typeinput'][0] the type to be recorded
    Return the username, magic identifier (these can be empty  strings) and the response action set."""
    response = []
    ## alter as required
    if handle_validate(iuser, imagic) != True:
        # Invalid sessions redirect to login
        response.append(build_response_redirect("/index.html"))
    elif iuser == "":
        response.append(build_response_redirect("/index.html"))
    elif imagic == "":
        response.append(build_response_redirect("/index.html"))
    else:  ## a valid session so process the addition of the entry.
        if "locationinput" not in parameters.keys():
            response.append(
                build_response_refill("message", "Please enter a valid location")
            )
        elif (
            "occpancyinput" in parameters.keys()
            or "typeinput" in parameters.keys()
            or "locationinput" in parameters.keys()
        ):
            try:
                total = 0
                location = parameters["locationinput"][0]
                occupancy = parameters["occupancyinput"][0]
                vehicle = parameters["typeinput"][0]

                if len(location) == 0 and occupancy == "two":
                    response.append(
                        build_response_refill(
                            "message", "Please enter a valid location"
                        )
                    )
                elif int(occupancy) >= 5:
                    response.append(build_response_refill("total", str(0)))
                else:
                    s_query = access_database_with_result(
                        "SELECT sessionid FROM session WHERE end = 0 AND magic='{}'".format(
                            imagic
                        )
                    )
                    v_d = {
                        "car": 0,
                        "van": 1,
                        "truck": 2,
                        "taxi": 3,
                        "other": 4,
                        "motorbike": 5,
                        "bicycle": 6,
                        "bus": 7,
                    }
                    vehicle_f = v_d[vehicle]
                    now = int(time.time())
                    sessionid = s_query[0][0]

                    access_database(
                        "INSERT INTO traffic (sessionid, time, type, occupancy, location, mode) VALUES ({}, {}, {}, {}, '{}', 1)".format(
                            sessionid, now, vehicle_f, occupancy, location
                        )
                    )

                    c_query = access_database_with_result(
                        "SELECT * FROM traffic WHERE mode=1 AND sessionid={}".format(
                            sessionid
                        )
                    )
                    total = len(c_query)
                    response.append(build_response_refill("message", "Entry Added"))
                    response.append(build_response_refill("total", str(total)))

            except KeyError:
                response.append(
                    build_response_refill("message", "Please enter a valid location")
                )
    user = ""
    magic = ""
    return [user, magic, response]


def handle_undo_request(iuser, imagic, parameters):
    """The user has requested a vehicle be removed from the count
    This is intended to allow counters to correct errors.
    parameters['locationinput'][0] the location to be recorded
    parameters['occupancyinput'][0] the occupant count to be recorded
    parameters['typeinput'][0] the type to be recorded
    Return the username, magic identifier (these can be empty  strings) and the response action set."""
    response = []
    ## alter as required
    if handle_validate(iuser, imagic) != True:
        # Invalid sessions redirect to login
        response.append(build_response_redirect("/index.html"))
        response.append(build_response_refill("message", "Please login!"))
    elif iuser == "":
        response.append(build_response_redirect("/index.html"))
        response.append(build_response_refill("message", "Please login!"))
    elif imagic == "":
        response.append(build_response_redirect("/index.html"))
        response.append(build_response_refill("message", "Please login!"))
    else:  ## a valid session so process the recording of the entry.
        ## FOR UNDO
        ## NOW NEED TO FIND sessionid to get the all match row to change the mode=1 into mode=2
        if "locationinput" not in parameters.keys():
            response.append(
                build_response_refill("message", "Please enter a valid location")
            )
        elif (
            "occpancyinput" in parameters.keys()
            or "typeinput" in parameters.keys()
            or "locationinput" in parameters.keys()
        ):
            vehicle = parameters["typeinput"][0]
            v_d = {
                "car": 0,
                "van": 1,
                "truck": 2,
                "taxi": 3,
                "other": 4,
                "motorbike": 5,
                "bicycle": 6,
                "bus": 7,
            }
            vehicle_f = v_d[vehicle]
            occupancy = parameters["occupancyinput"][0]
            location = parameters["locationinput"][0]

            try:
                query = access_database_with_result(
                    "SELECT recordid, sessionid FROM traffic \
                                                WHERE type = {} AND occupancy = {} AND location = '{}' AND mode = 1".format(
                        vehicle_f, occupancy, location
                    )
                )
                sessionid = query[0][1]
                recordid = query[-1][0]
                if len(query) > 0:
                    access_database(
                        "UPDATE traffic SET mode = 2 \
                                     WHERE recordid = {} AND sessionid = {} AND type = {} AND occupancy = {} AND location = '{}' AND mode=1".format(
                            recordid, sessionid, vehicle_f, occupancy, location
                        )
                    )
                    now = int(time.time())
                    access_database(
                        "INSERT INTO traffic (sessionid, time, type, occupancy, location, mode) \
                                    VALUES ({}, {}, {}, {}, '{}', 0)".format(
                            sessionid, now, vehicle_f, occupancy, location
                        )
                    )

                c_query = access_database_with_result(
                    "SELECT recordid FROM traffic WHERE mode=1"
                )
                total = len(c_query)
                response.append(build_response_refill("message", "Entry Un-done."))
                response.append(build_response_refill("total", str(total)))
            except:
                response.append(
                    build_response_refill(
                        "message", "No record found. Please try again!"
                    )
                )

    user = ""
    magic = ""
    return [user, magic, response]


def handle_back_request(iuser, imagic, parameters):
    """This code handles the selection of the back button on the record form (page.html)
    You will only need to modify this code if you make changes elsewhere that break its behaviour"""
    response = []
    ## alter as required
    if handle_validate(iuser, imagic) != True:
        response.append(build_response_redirect("/index.html"))
    else:
        response.append(build_response_redirect("/summary.html"))
    user = ""
    magic = ""
    return [user, magic, response]


def handle_summary_request(iuser, imagic, parameters):
    """This code handles a request for an update to the session summary values.
    You will need to extract this information from the database.
    You must return a value for all vehicle types, even when it's zero."""
    response = []
    ## alter as required
    if handle_validate(iuser, imagic) != True:
        # Invalid sessions redirect to login
        response.append(build_response_redirect("/index.html"))
        response.append(build_response_refill("message", "Please login!"))
    elif iuser == "":
        response.append(build_response_redirect("/index.html"))
        response.append(build_response_refill("message", "Please login!"))
    elif imagic == "":
        response.append(build_response_redirect("/index.html"))
        response.append(build_response_refill("message", "Please login!"))
    else:
        s_query = access_database_with_result(
            "SELECT sessionid FROM session WHERE end = 0 AND magic = '{}'".format(
                imagic
            )
        )
        session_id = s_query[0][0]
        # query = access_database_with_result("SELECT type, COUNT(type) FROM traffic WHERE mode = 1 OR mode = 2 GROUP BY type")
        sum_car = access_database_with_result(
            "SELECT COUNT(type) FROM traffic WHERE (type = 0 AND mode = 1) AND sessionid = '{}'".format(
                session_id
            )
        )[0][0]
        sum_taxi = access_database_with_result(
            "SELECT COUNT(type) FROM traffic WHERE (type = 3 AND mode = 1) AND sessionid = '{}'".format(
                session_id
            )
        )[0][0]
        sum_bus = access_database_with_result(
            "SELECT COUNT(type) FROM traffic WHERE (type = 7 AND mode = 1) AND sessionid = '{}'".format(
                session_id
            )
        )[0][0]
        sum_motorbike = access_database_with_result(
            "SELECT COUNT(type) FROM traffic WHERE (type = 5 AND mode = 1) AND sessionid = '{}'".format(
                session_id
            )
        )[0][0]
        sum_bicycle = access_database_with_result(
            "SELECT COUNT(type) FROM traffic WHERE (type = 6 AND mode = 1) AND sessionid = '{}'".format(
                session_id
            )
        )[0][0]
        sum_van = access_database_with_result(
            "SELECT COUNT(type) FROM traffic WHERE (type = 1 AND mode = 1) AND sessionid = '{}'".format(
                session_id
            )
        )[0][0]
        sum_truck = access_database_with_result(
            "SELECT COUNT(type) FROM traffic WHERE (type = 2 AND mode = 1) AND sessionid = '{}'".format(
                session_id
            )
        )[0][0]
        sum_other = access_database_with_result(
            "SELECT COUNT(type) FROM traffic WHERE (type = 4 AND mode = 1) AND sessionid = '{}'".format(
                session_id
            )
        )[0][0]

        total = (
            sum_car
            + sum_taxi
            + sum_bus
            + sum_bicycle
            + sum_motorbike
            + sum_van
            + sum_truck
            + sum_other
        )

        response.append(build_response_refill("sum_car", str(sum_car)))
        response.append(build_response_refill("sum_taxi", str(sum_taxi)))
        response.append(build_response_refill("sum_bus", str(sum_bus)))
        response.append(build_response_refill("sum_motorbike", str(sum_motorbike)))
        response.append(build_response_refill("sum_bicycle", str(sum_bicycle)))
        response.append(build_response_refill("sum_van", str(sum_van)))
        response.append(build_response_refill("sum_truck", str(sum_truck)))
        response.append(build_response_refill("sum_other", str(sum_other)))
        response.append(build_response_refill("total", str(total)))
        user = ""
        magic = ""
    return [user, magic, response]


# HTTPRequestHandler class
class myHTTPServer_RequestHandler(BaseHTTPRequestHandler):

    # GET This function responds to GET requests to the web server.
    def do_GET(self):

        # The set_cookies function adds/updates two cookies returned with a webpage.
        # These identify the user who is logged in. The first parameter identifies the user
        # and the second should be used to verify the login session.
        def set_cookies(x, user, magic):
            ucookie = Cookie.SimpleCookie()
            ucookie["u_cookie"] = user
            x.send_header("Set-Cookie", ucookie.output(header="", sep=""))
            mcookie = Cookie.SimpleCookie()
            mcookie["m_cookie"] = magic
            x.send_header("Set-Cookie", mcookie.output(header="", sep=""))

        # The get_cookies function returns the values of the user and magic cookies if they exist
        # it returns empty strings if they do not.
        def get_cookies(source):
            rcookies = Cookie.SimpleCookie(source.headers.get("Cookie"))
            user = ""
            magic = ""
            for keyc, valuec in rcookies.items():
                if keyc == "u_cookie":
                    user = valuec.value
                if keyc == "m_cookie":
                    magic = valuec.value
            return [user, magic]

        # Fetch the cookies that arrived with the GET request
        # The identify the user session.
        user_magic = get_cookies(self)

        print(user_magic)

        # Parse the GET request to identify the file requested and the parameters
        parsed_path = urllib.parse.urlparse(self.path)

        # Decided what to do based on the file requested.

        # Return a CSS (Cascading Style Sheet) file.
        # These tell the web client how the page should appear.
        if self.path.startswith("/css"):
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.end_headers()
            with open("." + self.path, "rb") as file:
                self.wfile.write(file.read())
            file.close()

        # Return a Javascript file.
        # These tell contain code that the web client can execute.
        elif self.path.startswith("/js"):
            self.send_response(200)
            self.send_header("Content-type", "text/js")
            self.end_headers()
            with open("." + self.path, "rb") as file:
                self.wfile.write(file.read())
            file.close()

        # A special case of '/' means return the index.html (homepage)
        # of a website
        elif parsed_path.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("./index.html", "rb") as file:
                self.wfile.write(file.read())
            file.close()

        # Return html pages.
        elif parsed_path.path.endswith(".html"):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("." + parsed_path.path, "rb") as file:
                self.wfile.write(file.read())
            file.close()

        # The special file 'action' is not a real file, it indicates an action
        # we wish the server to execute.
        elif parsed_path.path == "/action":
            self.send_response(200)  # respond that this is a valid page request
            # extract the parameters from the GET request.
            # These are passed to the handlers.
            parameters = urllib.parse.parse_qs(parsed_path.query)

            if "command" in parameters:
                # check if one of the parameters was 'command'
                # If it is, identify which command and call the appropriate handler function.
                if parameters["command"][0] == "login":
                    [user, magic, response] = handle_login_request(
                        user_magic[0], user_magic[1], parameters
                    )
                    # The result of a login attempt will be to set the cookies to identify the session.
                    set_cookies(self, user, magic)
                elif parameters["command"][0] == "add":
                    [user, magic, response] = handle_add_request(
                        user_magic[0], user_magic[1], parameters
                    )
                    if (
                        user == "!"
                    ):  # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, "", "")
                elif parameters["command"][0] == "undo":
                    [user, magic, response] = handle_undo_request(
                        user_magic[0], user_magic[1], parameters
                    )
                    if (
                        user == "!"
                    ):  # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, "", "")
                elif parameters["command"][0] == "back":
                    [user, magic, response] = handle_back_request(
                        user_magic[0], user_magic[1], parameters
                    )
                    if (
                        user == "!"
                    ):  # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, "", "")
                elif parameters["command"][0] == "summary":
                    [user, magic, response] = handle_summary_request(
                        user_magic[0], user_magic[1], parameters
                    )
                    if (
                        user == "!"
                    ):  # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, "", "")
                elif parameters["command"][0] == "logout":
                    [user, magic, response] = handle_logout_request(
                        user_magic[0], user_magic[1], parameters
                    )
                    if (
                        user == "!"
                    ):  # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, "", "")
                else:
                    # The command was not recognised, report that to the user.
                    response = []
                    response.append(
                        build_response_refill(
                            "message", "Internal Error: Command not recognised."
                        )
                    )

            else:
                # There was no command present, report that to the user.
                response = []
                response.append(
                    build_response_refill(
                        "message", "Internal Error: Command not found."
                    )
                )

            text = json.dumps(response)
            print(text)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(text, "utf-8"))

        ### OUTPUT CSV FILES
        elif self.path.endswith("/statistics/hours.csv"):
            ## if we get here, the user is looking for a statistics file
            ## this is where requests for /statistics/hours.csv should be handled.
            ## you should check a valid user is logged in. You are encouraged to wrap this behavour in a function.
            #### search for database for what they want
            #### put it into line by line
            #### delete the text lines here
            #### input every single line (\n)
            text = "Username,Day,Week,Month\n"

            today = time.strftime("%Y-%m-%d", time.gmtime(float(time.time())))
            start_time_today = time.mktime(
                datetime.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S").timetuple()
            )
            end_time_today = time.mktime(
                datetime.strptime(f"{today} 23:59:59", "%Y-%m-%d %H:%M:%S").timetuple()
            )

            week_today = dt.date.today()
            last_week = week_today - dt.timedelta(days=6)
            start_time_week = time.mktime(
                datetime.strptime(
                    f"{last_week} 00:00:00", "%Y-%m-%d %H:%M:%S"
                ).timetuple()
            )
            end_time_week = time.mktime(
                datetime.strptime(
                    f"{week_today} 23:59:59", "%Y-%m-%d %H:%M:%S"
                ).timetuple()
            )

            year = datetime.now().year
            month = datetime.now().month
            day = datetime.now().day
            last_year = 0
            last_month = 0
            last_date = 0

            if month == 1:
                last_month == 12
                last_year = year - 1
            else:
                last_month = month - 1
                last_year = year

            if day >= 30:
                last_date == 1
            elif day >= 28 and day < 30 and month == 3:
                last_date == 1
            else:
                last_date = day + 1

            finding_month_start = "{}-{:02d}-{:02d} 00:00:00".format(
                year, last_month, last_date
            )
            finding_month_end = "{}-{:02d}-{:02d} 23:59:59".format(year, month, day)
            start_time_month = int(
                dt.datetime.strptime(
                    f"{finding_month_start}", "%Y-%m-%d %H:%M:%S"
                ).strftime("%s")
            )
            end_time_month = int(
                dt.datetime.strptime(
                    f"{finding_month_end}", "%Y-%m-%d %H:%M:%S"
                ).strftime("%s")
            )

            day_query = access_database_with_result(
                "SELECT username, start, end FROM session \
                                                     INNER JOIN users ON session.userid = users.userid \
                                                     WHERE (start BETWEEN {} AND {}) AND (end BETWEEN {} AND {}) AND end != 0".format(
                    start_time_today, end_time_today, start_time_today, end_time_today
                )
            )
            special_day_query = access_database_with_result(
                "SELECT username, start, end FROM session \
                                                             INNER JOIN users ON session.userid = users.userid \
                                                             WHERE (start NOT BETWEEN '{}' AND '{}') AND (end BETWEEN '{}' AND '{}') AND end != 0".format(
                    start_time_today, end_time_today, start_time_today, end_time_today
                )
            )

            week_query = access_database_with_result(
                "SELECT username, start, end FROM session \
                                                      INNER JOIN users ON session.userid = users.userid \
                                                      WHERE (start BETWEEN {} AND {}) AND (end BETWEEN {} AND {}) AND end != 0".format(
                    start_time_week, end_time_week, start_time_week, end_time_week
                )
            )
            ## starting date not in what we want
            special_week_query = access_database_with_result(
                "SELECT username, start, end FROM session \
                                                                INNER JOIN users ON session.userid = users.userid \
                                                                WHERE (start NOT BETWEEN {} AND {}) AND (end BETWEEN {} AND {}) AND end != 0".format(
                    start_time_week, end_time_week, start_time_week, end_time_week
                )
            )

            month_query = access_database_with_result(
                "SELECT username, start, end FROM session \
                                                       INNER JOIN users ON session.userid = users.userid \
                                                       WHERE (start BETWEEN {} AND {}) AND (end BETWEEN {} AND {}) AND end != 0".format(
                    start_time_month, end_time_month, start_time_month, end_time_month
                )
            )
            special_month_query = access_database_with_result(
                "SELECT username, start, end FROM session \
                                                               INNER JOIN users ON session.userid = users.userid \
                                                               WHERE (start NOT BETWEEN {} AND {}) AND (end BETWEEN {} AND {}) AND end != 0".format(
                    start_time_month, end_time_month, start_time_month, end_time_month
                )
            )

            test1 = [0, 0, 0]
            test2 = [0, 0, 0]
            test3 = [0, 0, 0]
            test4 = [0, 0, 0]
            test5 = [0, 0, 0]
            test6 = [0, 0, 0]
            test7 = [0, 0, 0]
            test8 = [0, 0, 0]
            test9 = [0, 0, 0]
            test10 = [0, 0, 0]

            if len(day_query) > 0:
                for i in day_query:
                    if i[0] == "test1":
                        sec = i[2] - i[1]
                        test1[0] += sec
                    elif i[0] == "test2":
                        sec = i[2] - i[1]
                        test2[0] += sec
                    elif i[0] == "test3":
                        sec = i[2] - i[1]
                        test3[0] += sec
                    elif i[0] == "test4":
                        sec = i[2] - i[1]
                        test4[0] += sec
                    elif i[0] == "test5":
                        sec = i[2] - i[1]
                        test5[0] += sec
                    elif i[0] == "test6":
                        sec = i[2] - i[1]
                        test6[0] += sec
                    elif i[0] == "test7":
                        sec = i[2] - i[1]
                        test7[0] += sec
                    elif i[0] == "test8":
                        sec = i[2] - i[1]
                        test8[0] += sec
                    elif i[0] == "test9":
                        sec = i[2] - i[1]
                        test9[0] += sec
                    elif i[0] == "test10":
                        sec = i[2] - i[1]
                        test10[0] += sec

            if len(special_day_query) > 0:
                diff_day = [[i[0], i[2] - start_time_today] for i in special_day_query]
                for i in diff_day:
                    if i[0] == "test1":
                        test1[0] += i[1]
                    elif i[0] == "test2":
                        test2[0] += i[1]
                    elif i[0] == "test3":
                        test3[0] += i[1]
                    elif i[0] == "test4":
                        test4[0] += sec
                    elif i[0] == "test5":
                        test5[0] += i[1]
                    elif i[0] == "test6":
                        test6[0] += i[1]
                    elif i[0] == "test7":
                        test7[0] += i[1]
                    elif i[0] == "test8":
                        test8[0] += i[1]
                    elif i[0] == "test9":
                        test9[0] += i[1]
                    elif i[0] == "test10":
                        test10[0] += i[1]

            if len(week_query) > 0:
                for i in week_query:
                    if i[0] == "test1":
                        sec = i[2] - i[1]
                        test1[1] += sec
                    elif i[0] == "test2":
                        sec = i[2] - i[1]
                        test2[1] += sec
                    elif i[0] == "test3":
                        sec = i[2] - i[1]
                        test3[1] += sec
                    elif i[0] == "test4":
                        sec = i[2] - i[1]
                        test4[1] += sec
                    elif i[0] == "test5":
                        sec = i[2] - i[1]
                        test5[1] += sec
                    elif i[0] == "test6":
                        sec = i[2] - i[1]
                        test6[1] += sec
                    elif i[0] == "test7":
                        sec = i[2] - i[1]
                        test7[1] += sec
                    elif i[0] == "test8":
                        sec = i[2] - i[1]
                        test8[1] += sec
                    elif i[0] == "test9":
                        sec = i[2] - i[1]
                        test9[1] += sec
                    elif i[0] == "test10":
                        sec = i[2] - i[1]
                        test10[1] += sec

            if len(special_week_query) > 0:
                diff_week = [[i[0], i[2] - start_time_week] for i in special_week_query]
                for i in diff_week:
                    if i[0] == "test1":
                        test1[1] += i[1]
                    elif i[0] == "test2":
                        test2[1] += i[1]
                    elif i[0] == "test3":
                        test3[1] += i[1]
                    elif i[0] == "test4":
                        test4[1] += sec
                    elif i[0] == "test5":
                        test5[1] += i[1]
                    elif i[0] == "test6":
                        test6[1] += i[1]
                    elif i[0] == "test7":
                        test7[1] += i[1]
                    elif i[0] == "test8":
                        test8[1] += i[1]
                    elif i[0] == "test9":
                        test9[1] += i[1]
                    elif i[0] == "test10":
                        test10[1] += i[1]

            if len(month_query) > 0:
                for i in month_query:
                    if i[0] == "test1":
                        sec = i[2] - i[1]
                        test1[2] += sec
                    elif i[0] == "test2":
                        sec = i[2] - i[1]
                        test2[2] += sec
                    elif i[0] == "test3":
                        sec = i[2] - i[1]
                        test3[2] += sec
                    elif i[0] == "test4":
                        sec = i[2] - i[1]
                        test4[2] += sec
                    elif i[0] == "test5":
                        sec = i[2] - i[1]
                        test5[2] += sec
                    elif i[0] == "test6":
                        sec = i[2] - i[1]
                        test6[2] += sec
                    elif i[0] == "test7":
                        sec = i[2] - i[1]
                        test7[2] += sec
                    elif i[0] == "test8":
                        sec = i[2] - i[1]
                        test8[2] += sec
                    elif i[0] == "test9":
                        sec = i[2] - i[1]
                        test9[2] += sec
                    elif i[0] == "test10":
                        sec = i[2] - i[1]
                        test10[2] += sec

            if len(special_month_query) > 0:
                for i in special_month_query:
                    diff_month = [
                        [i[0], i[2] - start_time_month] for i in special_month_query
                    ]
                    if i[0] == "test1":
                        test1[2] += i[1]
                    elif i[0] == "test2":
                        test2[2] += i[1]
                    elif i[0] == "test3":
                        test3[2] += i[1]
                    elif i[0] == "test4":
                        test4[2] += sec
                    elif i[0] == "test5":
                        test5[2] += i[1]
                    elif i[0] == "test6":
                        test6[2] += i[1]
                    elif i[0] == "test7":
                        test7[2] += i[1]
                    elif i[0] == "test8":
                        test8[2] += i[1]
                    elif i[0] == "test9":
                        test9[2] += i[1]
                    elif i[0] == "test10":
                        test10[2] += i[1]

            text += "test1,{},{},{}\n".format(
                round((test1[0] / 3600), 1),
                round((test1[1] / 3600), 1),
                round((test1[2] / 3600), 1),
            )
            text += "test2,{},{},{}\n".format(
                round((test2[0] / 3600), 1),
                round((test2[1] / 3600), 1),
                round((test2[2] / 3600), 1),
            )
            text += "test3,{},{},{}\n".format(
                round((test3[0] / 3600), 1),
                round((test3[1] / 3600), 1),
                round((test3[2] / 3600), 1),
            )
            text += "test4,{},{},{}\n".format(
                round((test4[0] / 3600), 1),
                round((test4[1] / 3600), 1),
                round((test4[2] / 3600), 1),
            )
            text += "test5,{},{},{}\n".format(
                round((test5[0] / 3600), 1),
                round((test5[1] / 3600), 1),
                round((test5[2] / 3600), 1),
            )
            text += "test6,{},{},{}\n".format(
                round((test6[0] / 3600), 1),
                round((test6[1] / 3600), 1),
                round((test6[2] / 3600), 1),
            )
            text += "test7,{},{},{}\n".format(
                round((test7[0] / 3600), 1),
                round((test7[1] / 3600), 1),
                round((test7[2] / 3600), 1),
            )
            text += "test8,{},{},{}\n".format(
                round((test8[0] / 3600), 1),
                round((test8[1] / 3600), 1),
                round((test8[2] / 3600), 1),
            )
            text += "test9,{},{},{}\n".format(
                round((test9[0] / 3600), 1),
                round((test9[1] / 3600), 1),
                round((test9[2] / 3600), 1),
            )
            text += "test10,{},{},{}\n".format(
                round((test10[0] / 3600), 1),
                round((test10[1] / 3600), 1),
                round((test10[2] / 3600), 1),
            )

            encoded = bytes(text, "utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/csv")
            self.send_header(
                "Content-Disposition", 'attachment; filename="{}"'.format("hours.csv")
            )
            self.send_header("Content-Length", len(encoded))
            self.end_headers()
            self.wfile.write(encoded)

        elif self.path.endswith("/statistics/traffic.csv"):
            ## if we get here, the user is looking for a statistics file
            ## this is where requests for  /statistics/traffic.csv should be handled.
            ## you should check a valid user is checked in. You are encouraged to wrap this behavour in a function.

            ## CONDITION -- EACH DAY's DATA ONLY
            ## (NOT INCLUDE THE PREVIOUS DAY DATA)
            today = time.strftime("%Y-%m-%d", time.gmtime(float(time.time())))
            start_time = time.mktime(
                datetime.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S").timetuple()
            )
            end_time = time.mktime(
                datetime.strptime(f"{today} 23:59:59", "%Y-%m-%d %H:%M:%S").timetuple()
            )
            query = access_database_with_result(
                "SELECT location, type, occupancy,COUNT(*) FROM traffic \
                                                 WHERE mode=1 AND time BETWEEN {} AND {} \
                                                 GROUP BY location, type, occupancy".format(
                    start_time, end_time
                )
            )
            v_d = {
                0: "car",
                1: "van",
                2: "truck",
                3: "taxi",
                4: "other",
                5: "motorbike",
                6: "bicycle",
                7: "bus",
            }

            location = []
            type = []
            occupancy = []

            for i in range(len(query)):
                location.append(query[i][0])
                type.append(v_d[query[i][1]])
                # occupancy.append(o_d[query[i][2]])
                if query[i][2] == 1:
                    occupancy.append([query[i][3], 0, 0, 0])
                elif query[i][2] == 2:
                    occupancy.append([0, query[i][3], 0, 0])
                elif query[i][2] == 3:
                    occupancy.append([0, 0, query[i][3], 0])
                elif query[i][2] == 4:
                    occupancy.append([0, 0, 0, query[i][3]])

            # print(location, type, occupancy)

            text = "This should be the content of the csv file."
            text = "Location,Type,Occupancy1,Occupancy2,Occupancy3,Occupancy4\n"
            for i in range(len(location)):
                # text += '"Main Road",car,0,0,0,0\n' # not real data
                text += '"{}", {}, {}, {}, {}, {}\n'.format(
                    location[i],
                    type[i],
                    occupancy[i][0],
                    occupancy[i][1],
                    occupancy[i][2],
                    occupancy[i][3],
                )

            encoded = bytes(text, "utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/csv")
            self.send_header(
                "Content-Disposition", 'attachment; filename="{}"'.format("traffic.csv")
            )
            self.send_header("Content-Length", len(encoded))
            self.end_headers()
            self.wfile.write(encoded)

        else:
            # A file that does n't fit one of the patterns above was requested.
            self.send_response(404)
            self.end_headers()
        return


def run():
    """This is the entry point function to this code."""
    print("starting server...")
    ## You can add any extra start up code here
    #### clean the database and create a function
    #### delete all the contents in the table
    #### If I want to reset.
    #### Or just run .ipynb
    # Server settings
    # Choose port 8081 over port 80, which is normally used for a http server
    if len(sys.argv) < 2:  # Check we were given both the script name and a port number
        print("Port argument not provided.")
        return
    server_address = ("127.0.0.1", int(sys.argv[1]))
    httpd = HTTPServer(server_address, myHTTPServer_RequestHandler)
    print("running server on port =", sys.argv[1], "...")
    httpd.serve_forever()  # This function will not return till the server is aborted.


run()
