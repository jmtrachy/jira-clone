__author__ = 'James Trachy'

import configreader
import argparse
import base64
import getpass
import json
import ssl
import webtest

labels = {
    'c': 'wa-customersupport',
    'f': 'wa-feature',
    'o': 'wa-operations',
    'i': 'wa-infrastructure',
    't': 'wa-testautomation'
}

api_path = '/jira/rest/api/2/'
issue_path = '{}issue/'.format(api_path)
issue_link_path = '{}issueLink/'.format(api_path)


class Jira():

    def __init__(self, security_file, username=None, password=None):
        cr = configreader.PropertyReader(security_file)
        self.jira_host = cr.get_property('jira_host')

        if username is None:
            username = cr.get_property('username')
        if password is None:
            password = cr.get_property('password')

        self.encoded_credentials = base64.b64encode((username + ':' + password).encode("utf-8")).decode("utf-8")

    @staticmethod
    def cleanup_cloned_jira(self, ticket, label):
        cloned_jira = self.get_jira(ticket)

        subtasks = cloned_jira['fields']['subtasks']
        if len(subtasks) > 0:
            for subtask in subtasks:
                self.cleanup_cloned_subtask(subtask['key'])

        issue_links = cloned_jira['fields']['issuelinks']
        if len(issue_links) > 0:
            for link in issue_links:
                link_type = link['type']['name']
                if link_type == 'Cloners':
                    print('The link to ' + link['self'] + ' will be deleted.')
                    self.cleanup_cloned_link(ticket, link['id'], link['self'])

        self.assign_label(cloned_jira, label)

        return self.get_jira(ticket)

    def assign_label(self, cloned_jira, label):
        parsed_url = Jira.parse_host_and_uri(cloned_jira['self'])
        label_json = {
            'fields': {
                'labels': [
                    label
                ]
            }
        }

        req = webtest.HttpRequest()
        req.ssl = True
        req.body = json.dumps(label_json)
        req.headers[webtest._header_authorization] = 'Basic ' + self.encoded_credentials
        req.headers[webtest._header_content_type] = webtest._accept_JSON
        req.headers[webtest._header_accept] = webtest._accept_JSON
        req.host = parsed_url['host']
        req.url = parsed_url['path']
        req.method = 'PUT'

        response = webtest.WebService.send_request(req)
        if response['code'] > 299:
            raise Exception('Warning - response code = ' + str(response['code']) + '. You could get locked out after three attempts with the wrong password')

    def cleanup_cloned_link(self, issue_id, link_id, link_url):
        parsed_url = Jira.parse_host_and_uri(link_url)

        # Path to the actual link resource to delete
        del_path = issue_link_path + link_id

        req = webtest.HttpRequest()
        req.ssl = True
        req.method = 'DELETE'
        req.headers[webtest._header_authorization] = 'Basic ' + self.encoded_credentials
        req.headers[webtest._header_accept] = webtest._accept_JSON
        req.host = parsed_url['host']
        req.url = del_path

        response = webtest.WebService.send_request(req)
        if response['code'] > 299:
            raise Exception('Warning - response code = ' + str(response['code']) + '. You could get locked out after three attempts with the wrong password')
        elif response['code'] == 204:
            print('Deletion successful')

    def cleanup_cloned_subtask(self, ticket):
        cloned_subtask = Jira.get_jira(ticket)
        length_of_clone_string = 8
        summary = cloned_subtask['fields']['summary']

        if len(summary) >= length_of_clone_string:
            start_of_summary = summary[:length_of_clone_string]
            if start_of_summary == 'CLONE - ':
                print(cloned_subtask['key'] + ' - ' + summary + ' will be changed to ' + summary[length_of_clone_string:])
                Jira.update_jira_summary(cloned_subtask, summary[length_of_clone_string:])
            else:
                print(cloned_subtask['key'] + ' does not need to be changed - no action taken')

    def update_jira_summary(self, jira, new_summary):
        parsed_url = Jira.parse_host_and_uri(jira['self'])

        summary_json = {
            "fields": {
                "summary": new_summary
            }
        }

        req = webtest.HttpRequest()
        req.ssl = True
        req.body = json.dumps(summary_json)
        req.headers[webtest._header_authorization] = 'Basic ' + self.encoded_credentials
        req.headers[webtest._header_content_type] = webtest._accept_JSON
        req.headers[webtest._header_accept] = webtest._accept_JSON
        req.host = parsed_url['host']
        req.url = parsed_url['path']
        req.method = 'PUT'

        response = webtest.WebService.send_request(req)
        if response['code'] > 299:
            raise Exception('Warning - response code = ' + str(response['code']) + '. You could get locked out after three attempts with the wrong password')

    @staticmethod
    def parse_host_and_uri(url):
        parsed_request = {}
        first_slash = url.index('/', 8)
        parsed_request['host'] = url[8:first_slash]
        parsed_request['path'] = url[first_slash:]

        return parsed_request

    def get_jira(self, ticket):
        req = webtest.HttpRequest()

        req.ssl = True
        req.headers[webtest._header_authorization] = 'Basic ' + self.encoded_credentials
        req.headers[webtest._header_accept] = webtest._accept_JSON
        req.host = self.jira_host
        req.url = issue_path + ticket
        req.method = webtest._method_GET

        response = webtest.WebService.send_request(req)
        if response['code'] > 299:
            raise Exception('Warning - response code = ' + str(response['code']) + '. You could get locked out after three attempts with the wrong password')
        return json.loads(response['data'])

    def create_jira(self, jira_json):
        req = webtest.HttpRequest()

        req.ssl = True
        req.body = json.dumps(jira_json)
        req.headers[webtest._header_authorization] = 'Basic ' + self.encoded_credentials
        req.headers[webtest._header_accept] = webtest._accept_JSON
        req.headers[webtest._header_content_type] = webtest._accept_JSON
        req.host = self.jira_host
        req.url = issue_path
        req.method = webtest._method_POST

        response = webtest.WebService.send_request(req)
        if response['code'] > 299:
            print(response['data'])
            raise Exception('Warning - response code = ' + str(response['code']) + '. You could get locked out after three attempts with the wrong password')
        return json.loads(response['data'])

    def clone_jira(self, ticket, jira_to_replace, skip_label=False):
        # Get the existing jira
        jira_to_clone = self.get_jira(ticket)

        # Retrieve a wa- label if it exists
        wa_label = self.get_wa_label(skip_label, jira_to_clone)

        # Create json for the new jira
        clone_json = self.get_clone_json(jira_to_clone, wa_label)

        # Ask if the summary should be something different
        summary_input = 'Summary [' + jira_to_clone['fields']['summary'] + ']:'
        summary = input(summary_input)
        if not summary:
            summary = jira_to_clone['fields']['summary']

        summary = summary.replace(' - Skeleton to clone', '')

        if jira_to_replace:
            self.replace_jira_with_new(summary, clone_json, jira_to_replace)
        else:
            clone_json['fields']['summary'] = summary

        # Create the new jira
        new_jira = self.create_jira(clone_json)

        # Create subtasks
        self.add_subtasks(jira_to_clone, new_jira)

        # Return new jira - note it doesn't have its subtasks yet
        return new_jira

    def replace_jira_with_new(self, summary, clone_json, jira_to_replace):
        clone_json['fields']['summary'] = summary.replace('JIRA_TO_REPLACE', jira_to_replace)
        clone_json['fields']['description'] = clone_json['fields']['description'].replace('JIRA_TO_REPLACE', jira_to_replace)

    def add_subtasks(self, jira_to_clone, new_jira):
        existing_subtasks = jira_to_clone['fields']['subtasks']

        for es in existing_subtasks:
            existing_subtask = self.get_jira(es['key'])
            subtask_json = self.get_clone_json(existing_subtask, None)
            subtask_json['fields']['parent'] = {
                "id": new_jira['id']
            }
            subtask_json['fields']['summary'] = existing_subtask['fields']['summary']
            self.add_optional_field(existing_subtask, subtask_json, 'timetracking')

            self.create_jira(subtask_json)

    def add_optional_field(self, existing_issue, new_json, field):
        if field in existing_issue['fields']:
            new_json['fields'][field] = existing_issue['fields'][field]

    def get_wa_label(self, skip_label, existing_issue=None):
        label = None
        if existing_issue:
            labels_from_jira = existing_issue['fields']['labels']
            for lbl in labels_from_jira:
                if lbl[:3] == 'wa-':
                    label = lbl

        if label is None and not skip_label:
            label_key = ''
            while label_key not in labels:
                label_key = input('Label (wa-(c)ustomersupport, wa-(f)eature, wa-(o)perations, wa-(i)frastructure, wa-(t)estautomation:').lower()

            label = labels[label_key]

        return label

    def get_all_labels(self, existing_issue):
        labels = []
        labels_from_jira = existing_issue['fields']['labels']
        for lbl in labels_from_jira:
            if lbl[:3] != 'wa-':
                labels.append(lbl)

        return labels

    def get_clone_json(self, jira_to_clone, wa_label):
        fields = jira_to_clone['fields']

        components = fields['components']
        components_list = []
        for component in components:
            components_list.append({
                "id": component['id']
            })

        fix_versions = fields['fixVersions']
        fix_version_list = []
        for fix_version in fix_versions:
            fix_version_list.append({
                "id": fix_version['id']
            })

        affected_editions = fields['customfield_12301']
        affected_list = []
        for edition in affected_editions:
            affected_list.append({
                "id": edition['id']
            })

        new_jira_json = {
            "fields": {
                "project": {
                    "id": fields['project']['id']
                },
                "issuetype": {
                    "id": fields['issuetype']['id']
                },
                "assignee": {
                    "name": fields['assignee']['name']
                },
                "reporter": {
                    "name": fields['reporter']['name']
                },
                "priority": {
                    "id": fields['priority']['id']
                },
                "fixVersions": fix_version_list,
                "description": fields['description'],
                "components": components_list,
                "customfield_10310": {
                    "id": fields['customfield_10310']['id']
                },
                "customfield_10572": fields['customfield_10572'],
                "customfield_12301": affected_list
            }
        }

        existing_labels = self.get_all_labels(jira_to_clone)
        new_labels = []
        if existing_labels:
            new_labels = existing_labels

        if wa_label:
            new_labels.append(wa_label)

        new_jira_json['fields']['labels'] = new_labels

        return new_jira_json

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Gathering arguments')
    parser.add_argument('-j', required=False, dest='jira_ticket', action='store', help='An issue you would like to cleanup')
    parser.add_argument('-r', required=False, dest='jira_to_replace', action='store', help='Replaces the string JIRA_TO_REPLACE with this supplied string')
    parser.add_argument('-c', required=False, dest='jira_to_clone', action='store', help='An issue you would like to clone - including subtasks')
    parser.add_argument('-p', required=False, dest='props_file', default='config.properties', action='store', help='Provide configurations that you do not want to commit')
    parser.add_argument('-l', '--skip_label', action='store_true', help='Skip the work allocation label for this jira')
    parser.add_argument('-e', '--enter_password', action='store_true', help='Force me to enter my username and password - otherwise it will be read out of configuration')
    args = parser.parse_args()

    uname = None
    passwd = None

    if args.enter_password:
        uname = input('Username:')
        passwd = getpass.getpass('Password:')

    # Hack to get around [SSL: CERTIFICATE_VERIFY_FAILED] error
    ssl._create_default_https_context = ssl._create_unverified_context

    jira_cloner = Jira(args.props_file, uname, passwd)

    if args.jira_to_clone:
        jiras_to_clone = args.jira_to_clone.split(',')
        for jtc in jiras_to_clone:
            jtc_trimmed = jtc.strip()
            print('About to clone ' + jtc_trimmed)
            newly_cloned_jira = jira_cloner.clone_jira(jtc_trimmed, args.jira_to_replace, args.skip_label)
            print('Newly cloned issues available at: https://{}/jira/browse/{}'.format(jira_cloner.jira_host, newly_cloned_jira['key']))

    elif args.jira_ticket:
        l = jira_cloner.get_wa_label(False, None)
        scrubbed_jira = jira_cloner.cleanup_cloned_jira(args.jira_ticket, l)
        print('Scrubbed issue available at: https://{}/jira/browse/{}'.format(jira_cloner.jira_host, scrubbed_jira['key']))