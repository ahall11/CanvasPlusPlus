'''
* It Worked Yesterday...
* 2/7/17
* canvas.py
* Handles connection the Canvas Learning Management Software.
'''
from urllib import parse as parse
from urllib import request as request
from urllib import error as url_error
import logging
from enum import Enum
#from typing import Dict
from bs4 import BeautifulSoup
from tasks.models import DB_Tasks,DB_User,DB_Category,DB_TodoList
import logging
import json
import pprint
import codecs
import datetime
import sys


'''Global variables'''
reader = codecs.getreader('utf-8')  # This exists to help the json and urllib libraries work together.
pp = pprint.PrettyPrinter(indent=4)  # Print out larger, data objects in a readable manner.
service_url = "https://pacific.instructure.com/api/v1/"  # The site that we're pulling our data from.


class Service(Enum):
    ORIGINAL = 0
    CANVAS = 1


'''Pass in a Profile object'''
class User:
    def __init__(self, data, user_token):
        self.id = data['id']
        self.name = data['name']
        self.bio = data['bio']
        self.avatar_url = data['avatar_url']
        self.login_id = data['login_id']
        self.token = None
        self.user_token = user_token
        self.ToDoLists = []


    def __str__(self):
        to_return = ''
        to_return += "User ID: {}\nFull Name: {}\nLogin ID: {}"\
            .format(self.id, self.name, self.login_id)
        try:
            to_return += "\nBio: {}"\
                .format(self.bio)
        except KeyError:
            pass
        try:
            to_return += "\nFavorite Courses: "
            for course in self.ToDoLists:
                to_return += "\n\t{}".format(course.name)
        except TypeError:
             logging.error('Unable to pull courses from User class: TypeError')
        except KeyError:
            logging.error('Unable to pull courses from User class: KeyError')
        return to_return


    def add(self, data):
        # If the data is a list, the data is a list of course objects
        if type(data) is list:
            for course in data:
                to_do_list = TodoList(course, self.id, self.user_token)
                self.ToDoLists.append(to_do_list)
        # If the data is a string, the data is the user token
        elif type(data) is str:
            self.token = data
        else:
            logging.debug("Data type not recognized")


    def display(self):
        for course in self.ToDoLists:
            for assignment in course.assignment_tasks:
                print(assignment.assignment, ": " ,assignment.weight)


'''Pass in a Course object as data.'''
class TodoList:
    def __init__(self, data, user_id, user_token):
        self.canvas_id = data["id"]
        self.name = data["name"]
        self.canvas_account = data["account_id"]
        self.canvas_term = data["enrollment_term_id"]
        self.service = Service.CANVAS
        self.assignment_data = get_assignments(str(data['id']),user_token) # data id is the course id
        print(self.name, len(self.assignment_data))
        self.assignment_tasks = []
        self.user_id = user_id
        self.total = 0
        for assignment in self.assignment_data:
            todo = Assignment_Task(assignment, user_id)
            try:
                self.total += int(assignment['points_possible'])
            except:
                pass
            self.assignment_tasks.append(todo)
        for assignment in self.assignment_tasks:
            assignment.total_points = self.total
            assignment.calc_weight()


    def __str__(self):
        to_return = ''
        to_return +=\
            "Canvas ID: {}\nCourse Name: {}\nAssociated Account: {}\nTerm: {}\nAssignments: {}"\
            .format(self.canvas_id, self.name, self.canvas_account, self.canvas_term, self.__sizeof__())
        return to_return


    def __sizeof__(self):
        return len(self.assignment_tasks)


    def add(self, data):
        if type(data) is dict:
            self.todos.append(data)
        elif type(data) is list:
            self.assignment_tasks = self.assignment_tasks + data
        else:
            logging.debug("Data type not recognized")


class Assignment_Task:
    def __init__(self, data, user_id):
        # print(data)
        self.assignment = data['name']
        self.description = data['description']
        self.due_at = data['due_at']
        self.course_id = data['course_id']
        self.points_possible = data['points_possible']
        self.total_points=0
        self.weight = 0
        self.user_id = user_id


    def calc_weight(self):
        try: #self.points_possible is sometimes None, so weight is zero if this is the case
            self.weight= (self.points_possible/self.total_points)*100
        except:
            self.weight = 0


    def __str__(self):
        to_return = ''
        to_return += "Course ID: {}\nAssignment: {}\nDescription: {}\nDue Date: {}\nPoints: {}\n"\
                .format(self.course_id, self.assignment,self.description, self.due_at, self.points_possible)
        return to_return


'''Gets the url that contains the desired data. URL changes based on the user token and the mode.
@param mode: Represents the type of data that we're trying to recieve.'''
def get_url(mode, usertoken):
    return service_url + mode + '?' + parse.urlencode({'access_token': usertoken})


def get_data_from_url(url):
    # print(url)
    response = request.urlopen(url)
    obj = json.load(reader(response))
    return obj


def get_data(mode,usertoken):
    return get_data_from_url(get_url(mode,usertoken))


''' Gathering and returning user data objects'''
def get_user_token():
    try:
        token_file = open('usertoken.txt', 'r')
        token = token_file.read()
        token_file.close()
    except:
        token = input("Please enter your token value: ")
        token_file = open('usertoken.txt', 'w')
        token_file.write(token)
    return token


''' @return: User's profile if found, returns None if unable to retrieve
    @rtype: Profile'''
def get_user(usertoken):
    mode = "users/self/profile"
    try:
        return get_data(mode,usertoken)
    except (url_error.HTTPError, url_error.URLError, url_error.ContentTooShortError):
        logging.error('Unable to retrieve user data.')
        return None


''' @return: list of favorite courses or active courses if user has no favorite courses. Returns None if unable to retrieve
    @rtype: list of Favorite['context_type'] where context_type = "Course" '''
def get_favorite_courses(usertoken):
    mode = "users/self/favorites/courses"
    try:
        return get_data(mode, usertoken)
    except (url_error.HTTPError, url_error.URLError, url_error.ContentTooShortError):
        logging.error('Unable to retrieve favorite courses.')
        return None


''' Returns "Active" courses, which can be misleading if professor does not deactivate course after term end.
    @return: list of "Active" courses.
    @rtype: list of courses. '''
def get_courses(usertoken):
    mode = "courses"
    return get_data(mode, usertoken)


def get_assignments(course_id, usertoken):
    mode = "users/self/courses/" + course_id + "/assignments"
    try:
        return get_data_from_url(get_url(mode,usertoken)+ '&per_page=200')
        #return get_data(mode, usertoken)
    except (url_error.HTTPError, url_error.URLError, url_error.ContentTooShortError):
        logging.error('Unable to retrieve assignment list from each of your favorite courses.')
        return None


''' Returns an estimate of time needed to complete assignments for each course based on user input
    @return: dictionary of time estimates.
    @rtype: dictionary of courses and corresponding time values. '''
def time_estimate(usertoken):
    input_time = {}
    course_items = get_favorite_courses(usertoken)
    print("Enter the average amount of time needed [in minutes] to complete an assignment for the following class:")
    for course in course_items:
        time = input(course['name'] + ': ')
        input_time[course['name']] = time
    return input_time


def get_avatar_url(user_token):
    profile = get_user(user_token)
    return profile['avatar_url']


def add_assignments_DB(TodolistID, UserID, user_token):
    course_data = get_favorite_courses(user_token)
    count = 1
    for favorite_course in course_data:

        assignments_data = get_assignments(str(favorite_course['id']),user_token)
        for assignments in assignments_data:
            if str(datetime.datetime.now().isoformat()) <= str(assignments['due_at']):
                a = DB_Tasks(todo_list=TodolistID,user=UserID,task_name=assignments['name'],start_time=datetime, category=DB_Category.objects.get(id="1"),
                         end_time=assignments['due_at'],points=assignments.get('points_possible', 0),point_type=assignments.get('grading_type',"Default"),manual_rank = count, assignment_num=assignments['id'],
                         completed="f")
                count = count+1
                a.save()
            else:
                a = DB_Tasks(todo_list=TodolistID, user=UserID, task_name=assignments['name'], start_time=datetime,
                             category=DB_Category.objects.get(id="1"), end_time=assignments['due_at'],
                             points=handle_potential_none_points(assignments.get('points_possible', 0)),
                             point_type=assignments.get('grading_type',"Default"), manual_rank=count, assignment_num=assignments['id'],
                             completed="t")
                count = count + 1
                a.save()

def update_assignments_DB(TodolistID, UserID, user_token):
    course_data = get_favorite_courses(user_token)
    count = 1
    for favorite_course in course_data:
        assignments_data = get_assignments(str(favorite_course['id']),user_token)
        for assignments in assignments_data:
            try:
                a = DB_Tasks.objects.get(user=UserID, assignment_num = assignments['id'])
            except DB_Tasks.DoesNotExist:
                if str(datetime.datetime.now().isoformat()) <= str(assignments['due_at']):
                    a = DB_Tasks(todo_list=TodolistID, user=UserID, task_name=assignments['name'], start_time=datetime,
                                 category=DB_Category.objects.get(id="1"),
                                 end_time=assignments['due_at'], points=assignments.get('points_possible', 0),
                                 point_type=assignments.get('grading_type', "Default"), manual_rank=count,
                                 assignment_num=assignments['id'],
                                 completed="f")
                    count = count + 1
                    a.save()
                else:
                    a = DB_Tasks(todo_list=TodolistID, user=UserID, task_name=assignments['name'], start_time=datetime,
                                 category=DB_Category.objects.get(id="1"), end_time=assignments['due_at'],
                                 points=handle_potential_none_points(assignments.get('points_possible', 0)),
                                 point_type=assignments.get('grading_type', "Default"), manual_rank=count,
                                 assignment_num=assignments['id'],
                                 completed="t")
                    count = count + 1
                    a.save()

def handle_potential_none_points(points):
    if points is None:
        points = 0
    return points


def main():
    global user_token  # The token used to authenticate the user.
    user_token = get_user_token()
    user_data = get_user(user_token)
    user = User(user_data, user_token)
    user.add(get_favorite_courses(user_token))
    user.add(user_token)
    #pp.pprint(course_data)
    #time_needed = time_estimate(user_token)
    course_data2 = get_favorite_courses(user_token)
    for favorite_course in course_data2:

        assignments_data = get_assignments(str(favorite_course['id']), user_token)
        for assignments in assignments_data:
            print(assignments['name'])
    # Print Favorite Courses

    '''
    for favorite_course in course_data:
        #total = 0
        print('\t', favorite_course['name'])
        print('\t\t','Assignments From Course:')
        assignments_data = get_assignments(str(favorite_course['id']))
        # Print assignments in course

        for assignments in assignments_data:
            print('\t\t\t', assignments['name'])

            html = str(assignments['description'])
            soup = BeautifulSoup(html, "html.parser")
            print(soup.get_text())
            #print('\t\t\t\t', assignments['description'])
            print('\t\t\t\t', 'Available: ', assignments['unlock_at'], 'to', assignments['lock_at'])
            print('\t\t\t\t', 'Due: ', assignments['due_at'])
            print('\t\t\t\t', 'Points Possible: ', assignments['points_possible'])
            #total += int(assignments['points_possible'])
            print('\t\t\t\t', 'Assignment Weight: ', assignments.weight)
            print('\t\t\t\t', 'Grading Type: ', assignments['grading_type'])
            print('\t\t\t\t', 'Time Needed to Complete: ', time_needed[favorite_course['name']], " minutes")
        #print(favorite_course['name'], " Total Points: ", total)
    '''

    user.display()
    print("\nUser Object string output:")
    print(user)
