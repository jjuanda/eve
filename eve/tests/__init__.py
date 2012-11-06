import eve
from eve import Eve, STATUS_ERR
from datetime import datetime
import re
import unittest
import simplejson as json


class TestBase(unittest.TestCase):

    def setUp(self):
        reload(eve)
        self.app = Eve(settings='tests/testsettings.py')
        self.test_client = self.app.test_client()

        self.domain = self.app.config['DOMAIN']
        self.known_resource = 'contacts'
        self.known_resource_url = ('/%s/' %
                                   self.domain[self.known_resource]['url'])
        self.empty_resource = 'invoices'
        self.unknown_resource = 'unknown'
        self.unknown_item_id = '4f46445fc88e201858000000'
        self.unknown_item_name = 'unknown'

        self.unknown_item_id_url = ('/%s/%s/' %
                                    (self.domain[self.known_resource]['url'],
                                     self.unknown_item_id))
        self.unknown_item_name_url = ('/%s/%s/' %
                                      (self.domain[self.known_resource]['url'],
                                      self.unknown_item_name))

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert301(self, status):
        self.assertEqual(status, 301)

    def assert404(self, status):
        self.assertEqual(status, 404)

    def assert304(self, status):
        self.assertEqual(status, 304)


class TestMethodsBase(TestBase):

    def setUp(self):
        super(TestMethodsBase, self).setUp()
        response, status = self.get('contacts', '?max_results=2')
        contact = response['contacts'][0]
        self.item_id = contact[self.app.config['ID_FIELD']]
        self.item_name = contact['ref']
        self.item_etag = contact['etag']
        self.item_id_url = ('/%s/%s/' %
                            (self.domain[self.known_resource]['url'],
                             self.item_id))
        self.item_name_url = ('/%s/%s/' %
                              (self.domain[self.known_resource]['url'],
                               self.item_name))
        self.alt_ref = response['contacts'][1]['ref']

    def get(self, resource, query='', item=None):
        if resource in self.domain:
            resource = self.domain[resource]['url']
        if item:
            request = '/%s/%s/' % (resource, item)
        else:
            request = '/%s/%s' % (resource, query)

        r = self.test_client.get(request)
        return self.parse_response(r)

    def patch(self, url, data, headers=None):
        r = self.test_client.patch(url, self.content_type, data=data,
                                   headers=headers)
        return self.parse_response(r)

    def parse_response(self, r):
        v = json.loads(r.data)['response'] if r.status_code == 200 else None
        return v, r.status_code

    def assertValidationError(self, response, key, matches):
        self.assertTrue(key in response)
        k = response[key]
        self.assertTrue('status' in k)
        self.assertTrue(STATUS_ERR in k['status'])
        self.assertTrue('issues' in k)
        issues = k['issues']
        self.assertTrue(len(issues))

        for match in matches:
            self.assertTrue(match in issues[0][0])

    def assertExpires(self, resource):
        # TODO if we ever get access to response.date (it is None), compare
        # it with Expires
        r = self.test_client.get(resource)

        expires = r.headers.get('Expires')
        self.assertTrue(expires is not None)

    def assertCacheControl(self, resource):
        r = self.test_client.get(resource)

        cache_control = r.headers.get('Cache-Control')
        self.assertTrue(cache_control is not None)
        self.assertEqual(cache_control,
                         self.domain[self.known_resource]['cache_control'])

    def assertIfModifiedSince(self, resource):
        r = self.test_client.get(resource)

        last_modified = r.headers.get('Last-Modified')
        self.assertTrue(last_modified is not None)
        r = self.test_client.get(resource, headers=[('If-Modified-Since',
                                                    last_modified)])
        self.assert304(r.status_code)
        self.assertEqual(r.data, '')

    def assertItem(self, item):
        self.assertIs(type(item), dict)

        _id = item.get(self.app.config['ID_FIELD'])
        self.assertTrue(_id is not None)
        match = re.compile(self.app.config['ITEM_URL']).match(_id)
        self.assertTrue(match is not None)
        self.assertEqual(match.group(), _id)

        updated_on = item.get(self.app.config['LAST_UPDATED'])
        self.assertTrue(updated_on is not None)
        try:
            datetime.strptime(updated_on, self.app.config['DATE_FORMAT'])
        except Exception, e:
            self.fail('Cannot convert field "%s" to datetime: %s' %
                      (self.app.config['LAST_UPDATED'], e))

        link = item.get('link')
        self.assertTrue(link is not None)
        self.assertItemLink(link, _id)

    def assertHomeLink(self, links):
        found = False
        for link in links:
            if "title='home'" in link and \
               "href='%s'" % self.app.config['BASE_URI'] in link:
                found = True
                break
        self.assertTrue(found)

    def assertResourceLink(self, links, resource):
        url = self.domain[resource]['url']
        found = False
        for link in links:
            if "title='%s'" % url in link and \
               "href='%s/%s/" % (self.app.config['BASE_URI'], url) in link:
                found = True
                break
        self.assertTrue(found)

    def assertNextLink(self, links, page):
        found = False
        for link in links:
            if "title='next page'" in link and "rel='next'" in link and \
               'page=%d' % page in link:
                found = True
        self.assertTrue(found)

    def assertPrevLink(self, links, page):
        found = False
        for link in links:
            if "title='previous page'" in link and "rel='prev'" in link:
                if page > 1:
                    found = 'page=%d' % page in link
                else:
                    found = True
        self.assertTrue(found)

    def assertItemLink(self, link, item_id):
        self.assertTrue("rel='self'" in link and '/%s/' % item_id in link)

    def assert400(self, status):
        self.assertEqual(status, 400)

    def assert403(self, status):
        self.assertEqual(status, 403)

    def assert405(self, status):
        self.assertEqual(status, 405)

    def assert412(self, status):
        self.assertEqual(status, 412)
