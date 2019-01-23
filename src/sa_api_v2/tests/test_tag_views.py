from django.test import TestCase
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.core.cache import cache as django_cache
import json
from ..cors.models import Origin
from ..cache import cache_buffer
from ..models import (
    User,
    DataSet,
    Place,
    PlaceTag,
    Tag
)
from .test_views import APITestMixin
from ..views import (
    PlaceTagInstanceView
)
# ./src/manage.py test sa_api_v2.tests.test_tag_views:TestPlaceTagInstanceView.test_GET_response
# ./src/manage.py test sa_api_v2.tests.test_views:TestPlaceListView.test_POST_invisible_response


class TestPlaceTagInstanceView (APITestMixin, TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='aaron', password='123', email='abc@example.com')
        self.submitter = User.objects.create_user(username='mjumbe', password='456', email='123@example.com')
        self.dataset = DataSet.objects.create(slug='ds', owner=self.owner)
        self.place = Place.objects.create(
          dataset=self.dataset,
          geometry='POINT(2 3)',
          submitter=self.submitter,
          data=json.dumps({
            'type': 'ATM',
            'name': 'K-Mart',
            'private-secrets': 42
          }),
        )
        self.tags = [
            Tag.objects.create(
                name="status",
                dataset=self.dataset,
            ),
        ]

        self.tags.extend([
            Tag.objects.create(
                name="approved",
                dataset=self.dataset,
                parent=self.tags[0]
            ),
            Tag.objects.create(
                name="rejected",
                dataset=self.dataset,
                parent=self.tags[0]
            )
        ])

        self.place_tag = PlaceTag.objects.create(
            place=self.place,
            submitter=self.submitter,
            tag=self.tags[2],
            note="I approve this place!"
        )
            # ),
            # PlaceTag.objects.create(
            #     place=self.place,
            #     tag=self.tags[3],
            #     note="I reject this place!",
            # )
        # ]

        self.origin = Origin.objects.create(pattern='def', dataset=self.dataset)
        Origin.objects.create(pattern='def2', dataset=self.dataset)

        self.request_kwargs = {
          'owner_username': self.owner.username,
          'dataset_slug': self.dataset.slug,
          'place_id': self.place.id,
          'place_tag_id': self.place_tag.id
          # 'submission_set_name': 'comments',
          # 'submission_id': self.submission.id
        }

        self.factory = RequestFactory()
        self.path = reverse('place-tag-detail', kwargs=self.request_kwargs)
        self.view = PlaceTagInstanceView.as_view()

        cache_buffer.reset()
        django_cache.clear()

    def tearDown(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()  # this should delete all of the PlaceTags as well, (via cascade)

        # TODO: ensure that there are no more Tag or PlaceTag 's left

        # PlaceTag.objects.all().delete()
        # Tag.objects.all().delete()
        # Submission.objects.all().delete()
        # ApiKey.objects.all().delete()

        cache_buffer.reset()
        django_cache.clear()

    def test_GET_response(self):
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # # Check that data attribute is not present
        # self.assertNotIn('data', data)

        # # Check that the data attributes have been incorporated into the
        # # properties
        self.assertEqual(data.get('note'), "I approve this place!")

        # # Check that the appropriate attributes are in the properties
        self.assertIn('url', data)
        self.assertIn('submitter', data)
        self.assertIn('place', data)
        self.assertIn('tag', data)

        # # Check that the URL is right
        self.assertEqual(
            data['url'],
            'http://testserver' + reverse('place-tag-detail', args=[
                self.owner.username, self.dataset.slug, self.place.id,
                self.place_tag.id])
        )

    def test_GET_invalid_url(self):
        # Make sure that we respond with 404 if a place_id is supplied, but for
        # the wrong dataset or owner.
        request_kwargs = {
          'owner_username': 'mischevious_owner',
          'dataset_slug': self.dataset.slug,
          'place_id': self.place.id,
          'submission_set_name': 'comments',
          'submission_id': self.submission.id
        }

        path = reverse('submission-detail', kwargs=request_kwargs)
        request = self.factory.get(path)
        response = self.view(request, **request_kwargs)

        self.assertStatusCode(response, 404)

    # TODO: implement this when caching is re-enabled:
    # def test_GET_from_cache(self):
    #     path = reverse('submission-detail', kwargs=self.request_kwargs)
    #     request = self.factory.get(path)

    #     # Check that we make a finite number of queries
    #     #
    #     # ---- Checking data access permissions:
    #     #
    #     # - SELECT requested dataset and owner
    #     # - SELECT dataset permissions
    #     # - SELECT keys
    #     # - SELECT key permissions
    #     # - SELECT origins
    #     # - SELECT origin permissions
    #     #
    #     # ---- Build the data
    #     #
    #     # - SELECT * FROM sa_api_submission AS s
    #     #     JOIN sa_api_submittedthing AS st ON (s.submittedthing_ptr_id = st.id)
    #     #     JOIN sa_api_dataset AS ds ON (st.dataset_id = ds.id)
    #     #     JOIN sa_api_submissionset AS ss ON (s.parent_id = ss.id)
    #     #     JOIN sa_api_place AS p ON (ss.place_id = p.submittedthing_ptr_id)
    #     #     JOIN sa_api_submittedthing AS pt ON (p.submittedthing_ptr_id = pt.id)
    #     #    WHERE st.id = <self.submission.id>;
    #     #
    #     # - SELECT * FROM sa_api_attachment AS a
    #     #    WHERE a.thing_id IN (<self.submission.id>);
    #     #
    #     with self.assertNumQueries(13):
    #         response = self.view(request, **self.request_kwargs)
    #         self.assertStatusCode(response, 200)

    #     path = reverse('submission-detail', kwargs=self.request_kwargs)
    #     request = self.factory.get(path)

    #     # Check that this performs no more queries than required for auth,
    #     # since the data's all cached
    #     with self.assertNumQueries(0):
    #         response = self.view(request, **self.request_kwargs)
    #         self.assertStatusCode(response, 200)

    # def test_DELETE_response(self):
    #     #
    #     # View should 401 when trying to delete when not authenticated
    #     #
    #     request = self.factory.delete(self.path)
    #     response = self.view(request, **self.request_kwargs)
    #     self.assertStatusCode(response, 401)

    #     #
    #     # View should delete the place when owner is authenticated
    #     #
    #     request = self.factory.delete(self.path)
    #     # request.META[KEY_HEADER] = self.apikey.key
    #     response = self.view(request, **self.request_kwargs)

    #     # Check that the request was successful
    #     self.assertStatusCode(response, 204)

    #     # Check that no data was returned
    #     self.assertIsNone(response.data)

    # def test_PUT_response(self):
    #     submission_data = json.dumps({
    #       'comment': 'Revised opinion',
    #       'private-email': 'newemail@gmail.com'
    #     })

    #     #
    #     # View should 401 when trying to update when not authenticated
    #     #
    #     request = self.factory.put(self.path, data=submission_data, content_type='application/json')
    #     response = self.view(request, **self.request_kwargs)
    #     self.assertStatusCode(response, 401)

    #     #
    #     # View should update the place when owner is authenticated
    #     #
    #     request = self.factory.put(self.path, data=submission_data, content_type='application/json')
    #     # request.META[KEY_HEADER] = self.apikey.key

    #     response = self.view(request, **self.request_kwargs)

    #     data = json.loads(response.rendered_content)

    #     # Check that the request was successful
    #     self.assertStatusCode(response, 200)

    #     # Check that the data attributes have been incorporated into the
    #     # properties
    #     self.assertEqual(data.get('comment'), 'Revised opinion')

    #     # submitter is special, and so should be present and None
    #     self.assertIsNone(data['submitter'])

    #     # foo is not special (lives in the data blob), so should just be unset
    #     self.assertNotIn('foo', data)

    #     # private-email is not special, but is private, so should not come
    #     # back down
    #     self.assertNotIn('private-email', data)


class TestPlaceTagListView (APITestMixin, TestCase):
    def setUp(self):
        cache_buffer.reset()
        django_cache.clear()

        self.owner_password = '123'
        self.owner = User.objects.create_user(
            username='aaron',
            password=self.owner_password,
            email='abc@example.com')
        self.submitter = User.objects.create_user(
            username='mjumbe',
            password='456',
            email='123@example.com')
        self.dataset = DataSet.objects.create(slug='ds', owner=self.owner)
        self.place = Place.objects.create(
          dataset=self.dataset,
          geometry='POINT(2 3)',
          submitter=self.submitter,
          data=json.dumps({
            'type': 'ATM',
            'name': 'K-Mart',
            'private-secrets': 42
          }),
        )
        self.invisible_place = Place.objects.create(
          dataset=self.dataset,
          geometry='POINT(3 4)',
          submitter=self.submitter,
          visible=False,
          data=json.dumps({
            'type': 'ATM',
            'name': 'Walmart',
          }),
        )
        # These are mainly around to ensure that we don't get spillover from
        # other datasets.
        dataset2 = DataSet.objects.create(slug='ds2', owner=self.owner)
        place2 = Place.objects.create(
          dataset=dataset2,
          geometry='POINT(3 4)',
        )
        # submissions2 = [
        #   Submission.objects.create(place_model=place2, set_name='comments', dataset=dataset2, data='{"comment": "Wow!", "private-email": "abc@example.com", "foo": 3}'),
        #   Submission.objects.create(place_model=place2, set_name='comments', dataset=dataset2, data='{"foo": 3}'),
        #   Submission.objects.create(place_model=place2, set_name='comments', dataset=dataset2, data='{"foo": 3}', visible=False),
        # ]

        # self.apikey = ApiKey.objects.create(key='abc', dataset=self.dataset)

        self.request_kwargs = {
          'owner_username': self.owner.username,
          'dataset_slug': self.dataset.slug,
          'place_id': self.place.id,
          'submission_set_name': self.submission.set_name
        }

        self.factory = RequestFactory()
        self.path = reverse('submission-list', kwargs=self.request_kwargs)
        self.view = SubmissionListView.as_view()

    def tearDown(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        # Submission.objects.all().delete()
        # ApiKey.objects.all().delete()

        cache_buffer.reset()
        django_cache.clear()

    def test_OPTIONS_response(self):
        request = self.factory.options(self.path)
        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

    def test_OPTIONS_response_as_owner(self):
        request = self.factory.options(self.path)
        request.user = self.owner
        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

    def test_GET_response(self):
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that it's a results collection
        self.assertIn('results', data)
        self.assertIn('metadata', data)

        # Check that the metadata looks right
        self.assertIn('length', data['metadata'])
        self.assertIn('next', data['metadata'])
        self.assertIn('previous', data['metadata'])
        self.assertIn('page', data['metadata'])

        # Check that we have the right number of results
        self.assertEqual(len(data['results']), 2)

        self.assertEqual(data['results'][-1]['url'],
            'http://testserver' + reverse('submission-detail', args=[
                self.owner.username, self.dataset.slug, self.place.id,
                self.submission.set_name, self.submission.id]))

    # def test_GET_response_for_multiple_specific_objects(self):
    #     submissions = []
    #     for _ in range(10):
    #         submissions.append(Submission.objects.create(place_model=self.place, set_name='comments', dataset=self.dataset, data='{"comment": "Wow!", "private-email": "abc@example.com", "foo": 3}'))

    #     request_kwargs = {
    #       'owner_username': self.owner.username,
    #       'dataset_slug': self.dataset.slug,
    #       'place_id': self.place.id,
    #       'submission_set_name': self.submission.set_name,
    #       'pk_list': ','.join([str(s.pk) for s in submissions[::2]])
    #     }

    #     factory = RequestFactory()
    #     path = reverse('submission-list', kwargs=request_kwargs)
    #     view = SubmissionListView.as_view()

    #     request = factory.get(path)
    #     response = view(request, **request_kwargs)
    #     data = json.loads(response.rendered_content)

    #     # Check that the request was successful
    #     self.assertStatusCode(response, 200)

    #     # Check that it's a results collection
    #     self.assertIn('results', data)

    #     # Check that we have the right number of results
    #     self.assertEqual(len(data['results']), 5)

    #     # Check that the pks are correct
    #     self.assertEqual(
    #         set([r['id'] for r in data['results']]),
    #         set([s.pk for s in submissions[::2]])
    #     )

    # def test_GET_csv_response(self):
    #     request = self.factory.get(self.path + '?format=csv')
    #     response = self.view(request, **self.request_kwargs)

    #     rows = list(csv.reader(StringIO(response.rendered_content)))
    #     headers = rows[0]

    #     # Check that the request was successful
    #     self.assertStatusCode(response, 200)

    #     # Check that it's got good headers
    #     self.assertIn('dataset', headers)
    #     self.assertIn('comment', headers)
    #     self.assertIn('foo', headers)

    #     # Check that we have the right number of rows
    #     self.assertEqual(len(rows), 3)

    def test_GET_invalid_url(self):
        # Make sure that we respond with 404 if a slug is supplied, but for
        # the wrong dataset or owner.
        request_kwargs = {
          'owner_username': 'mischevious_owner',
          'dataset_slug': self.dataset.slug,
          'place_id': self.place.id,
          'submission_set_name': self.submission.set_name
        }

        path = reverse('submission-list', kwargs=request_kwargs)
        request = self.factory.get(path)
        response = self.view(request, **request_kwargs)

        self.assertStatusCode(response, 404)

    def test_POST_response(self):
        submission_data = json.dumps({
          'submitter_name': 'Andy',
          'private-email': 'abc@example.com',
          'foo': 'bar'
        })
        start_num_submissions = Submission.objects.all().count()

        #
        # View should 401 when trying to create when not authenticated
        #
        request = self.factory.post(self.path, data=submission_data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should create the submission and set when owner is authenticated
        #
        request = self.factory.post(self.path, data=submission_data, content_type='application/json')
        # request.META[KEY_HEADER] = self.apikey.key

        response = self.view(request, **self.request_kwargs)

        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 201)

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data.get('foo'), 'bar')
        self.assertEqual(data.get('submitter_name'), 'Andy')

        # visible should be true by default
        self.assert_(data.get('visible'))

        # private-secrets is not special, but is private, so should not come
        # back down
        self.assertNotIn('private-email', data)

        # Check that we actually created a submission and set
        final_num_submissions = Submission.objects.all().count()
        self.assertEqual(final_num_submissions, start_num_submissions + 1)

    def test_POST_response_without_data_permission(self):
        submission_data = json.dumps({
          'submitter_name': 'Andy',
          'private-email': 'abc@example.com',
          'foo': 'bar'
        })
        start_num_submissions = Submission.objects.all().count()

        # Disable create permission
        key_permission = self.apikey.permissions.all().get()
        key_permission.can_create = False
        key_permission.save()

        #
        # View should 401 when trying to create
        #
        request = self.factory.post(self.path, data=submission_data, content_type='application/json')
        # request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 403)

    def test_POST_response_with_submitter(self):
        submission_data = json.dumps({
          'private-email': 'abc@example.com',
          'foo': 'bar'
        })
        start_num_submissions = Submission.objects.all().count()

        #
        # View should 401 when trying to create when not authenticated
        #
        request = self.factory.post(self.path, data=submission_data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should create the submission and set when owner is authenticated
        #
        request = self.factory.post(self.path, data=submission_data, content_type='application/json')
        # request.META[KEY_HEADER] = self.apikey.key
        request.user = self.submitter
        request.csrf_processing_done = True

        response = self.view(request, **self.request_kwargs)

        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 201)

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data.get('foo'), 'bar')

        self.assertIn('submitter', data)
        self.assertIsNotNone(data['submitter'])
        self.assertEqual(data['submitter']['id'], self.submitter.id)

        # visible should be true by default
        self.assert_(data.get('visible'))

        # private-secrets is not special, but is private, so should not come
        # back down
        self.assertNotIn('private-email', data)

        # Check that we actually created a submission and set
        final_num_submissions = Submission.objects.all().count()
        self.assertEqual(final_num_submissions, start_num_submissions + 1)

    def test_PUT_creates_in_bulk(self):
        # Create a couple bogus places so that we can be sure we're not
        # inadvertantly deleting them
        Submission.objects.create(dataset=self.dataset, place_model=self.place, set_name='comments')
        Submission.objects.create(dataset=self.dataset, place_model=self.place, set_name='comments')

        # Make some data that will update the place, and create another
        submission_data = json.dumps([
            {
                'submitter_name': 'Andy',
                'private-email': 'abc@example.com',
                'foo': 'bar'
            },
            {
                'submitter_name': 'Mjumbe',
                'private-email': 'def@example.com',
                'foo': 'baz'
            }
        ])
        start_num_submissions = Submission.objects.all().count()

        #
        # View should 401 when trying to update when not authenticated
        #
        request = self.factory.put(self.path, data=submission_data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should update the places when owner is authenticated
        #
        request = self.factory.put(self.path, data=submission_data, content_type='application/json')
        # request.META[KEY_HEADER] = self.apikey.key

        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        data_list = json.loads(response.rendered_content)

        self.assertEqual(len(data_list), 2)

        ### Check that we actually created the places
        final_num_submissions = Submission.objects.all().count()
        self.assertEqual(final_num_submissions, start_num_submissions + 2)

    def test_PUT_response_creates_and_updates_at_once(self):
        # Create a couple bogus places so that we can be sure we're not
        # inadvertantly deleting them
        Submission.objects.create(dataset=self.dataset, place_model=self.place, set_name='comments')
        Submission.objects.create(dataset=self.dataset, place_model=self.place, set_name='comments')

        # Create a submission
        submission = Submission.objects.create(dataset=self.dataset, place_model=self.place, set_name='comments')

        # Make some data that will update the submission, and create another
        submission_data = json.dumps([
            {
                'submitter_name': 'Andy',
                'private-email': 'abc@example.com',
                'foo': 'bar',
                'id': submission.id,
                'url': 'http://testserver/api/v2/aaron/datasets/ds/places/%s/comments/%s' % (self.place.id, submission.id)
            },
            {
                'submitter_name': 'Mjumbe',
                'private-email': 'def@example.com',
                'foo': 'baz'
            }
        ])
        start_num_submissions = Submission.objects.all().count()

        #
        # View should 401 when trying to update when not authenticated
        #
        request = self.factory.put(self.path, data=submission_data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should update the places when owner is authenticated
        #
        request = self.factory.put(self.path, data=submission_data, content_type='application/json')
        # request.META[KEY_HEADER] = self.apikey.key

        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        data_list = json.loads(response.rendered_content)

        self.assertEqual(len(data_list), 2)

        ### Check the updated item
        data = [item for item in data_list if item['id'] == submission.id][0]

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data.get('foo'), 'bar')
        self.assertEqual(data.get('submitter_name'), 'Andy')

        # visible should be true by default
        self.assert_(data.get('visible'))

        # private-secrets is not special, but is private, so should not come
        # back down
        self.assertNotIn('private-email', data)

        ### Check the created item
        data = [item for item in data_list if item['id'] != submission.id][0]

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data.get('foo'), 'baz')
        self.assertEqual(data.get('submitter_name'), 'Mjumbe')

        ### Check that we actually created the places
        final_num_submissions = Submission.objects.all().count()
        self.assertEqual(final_num_submissions, start_num_submissions + 1)


