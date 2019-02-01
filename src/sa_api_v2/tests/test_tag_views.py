from django.test import TestCase
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.core.cache import cache as django_cache
import json
from ..cors.models import Origin
from ..cache import cache_buffer
from ..models import (
    User,
    DataSet,
    Place,
    PlaceTag,
    Tag,
    Group,
    GroupPermission
)
from .test_views import APITestMixin
from ..views import (
    PlaceTagInstanceView,
    PlaceTagListView
)
# ./src/manage.py test -s sa_api_v2.tests.test_tag_views:TestPlaceTagListView.test_POST_response_with_invalid_tag
# ./src/manage.py test -s sa_api_v2.tests.test_views:TestPlaceListView.test_POST_invisible_response


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
            tag=self.tags[1],
            note="I approve this place!"
        )

        self.origin = Origin.objects.create(pattern='def', dataset=self.dataset)
        Origin.objects.create(pattern='def2', dataset=self.dataset)

        self.unauthorized_user = User.objects.create_user(
            username='temp_user',
            password='lkjasdf'
        )
        self.authorized_user = User.objects.create_user(
            username='temp_user2',
            password='lkjasdf'
        )
        group = Group.objects.create(
            dataset=self.dataset,
            name='mygroup'
        )
        group.submitters.add(self.authorized_user)
        GroupPermission.objects.create(
            group=group,
            # TODO: rename this to 'resource':
            submission_set='tags',
            can_destroy=True,
            can_update=True
        )
        unauthorized_group = Group.objects.create(
            dataset=self.dataset,
            name='badgroup'
        )
        unauthorized_group.submitters.add(self.unauthorized_user)
        unauthorized_group.submitters.add(self.authorized_user)
        GroupPermission.objects.create(
            group=unauthorized_group,
            # TODO: rename this to 'resource':
            submission_set='tags',
        )

        self.request_kwargs = {
          'owner_username': self.owner.username,
          'dataset_slug': self.dataset.slug,
          'place_id': self.place.id,
          'place_tag_id': self.place_tag.id
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
        Tag.objects.all().delete()  # this should delete all of the PlaceTags as well, (via cascade)

        # TODO: ensure that there are no more Tag or PlaceTag 's left

        # PlaceTag.objects.all().delete()
        cache_buffer.reset()
        django_cache.clear()

    def test_GET_response(self):
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data.get('note'), "I approve this place!")

        # Check that the appropriate attributes are in the properties
        self.assertIn('url', data)
        self.assertIn('submitter', data)
        self.assertIn('place', data)
        self.assertIn('tag', data)

        # Check that the URL is right
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
          'place_tag_id': self.place_tag.id
        }

        path = reverse('place-tag-detail', kwargs=request_kwargs)
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

    def test_DELETE_response(self):
        #
        # View should 401 when trying to delete when not authenticated
        #
        request = self.factory.delete(self.path)
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should 403 the place when user is unauthorized
        #
        request = self.factory.delete(self.path)
        request.user = self.unauthorized_user
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 403)

        #
        # View should delete the place when owner is authenticated
        #
        request = self.factory.delete(self.path)
        request.user = self.authorized_user
        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 204)

        # Check that no data was returned
        self.assertIsNone(response.data)

    def test_PUT_response(self):
        submission_data = json.dumps({
          'note': 'Revised comment',
        })
        # TODO: get json from django model, merge with submission data to fix PUT
        # import ipdb
        # ipdb.set_trace()

        #
        # View should 401 when trying to update when not authenticated
        #
        request = self.factory.put(self.path, data=submission_data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should 403 when trying to update when not authorized
        #
        # user = User.objects.create_user(username='temp_user',
        #                                 password='lkjasdf')
        request = self.factory.put(self.path, data=submission_data, content_type='application/json')
        request.user = self.unauthorized_user
        request.META['HTTP_ORIGIN'] = self.origin.pattern
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 403)

        # #
        # # View should 200 when trying to update when authorized
        # #
        # request = self.factory.put(self.path, data=submission_data, content_type='application/json')
        # request.user = self.authorized_user
        # request.META['HTTP_ORIGIN'] = self.origin.pattern
        # response = self.view(request, **self.request_kwargs)
        # self.assertStatusCode(response, 403)

    def test_PATCH_response(self):
        submission_data = json.dumps({
          'note': 'Revised comment',
        })
        #
        # View should update the place when user is authenticated
        #
        request = self.factory.patch(self.path, data=submission_data, content_type='application/json')
        request.user = self.authorized_user
        request.META['HTTP_ORIGIN'] = self.origin.pattern
        response = self.view(request, **self.request_kwargs)

        # # Check that the request was successful
        self.assertStatusCode(response, 200)

        data = json.loads(response.rendered_content)

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data.get('note'), 'Revised comment')


class TestPlaceTagListView (APITestMixin, TestCase):
    def setUp(self):

        cache_buffer.reset()
        django_cache.clear()

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

        self.place_tags = [
            PlaceTag.objects.create(
                place=self.place,
                submitter=self.submitter,
                tag=self.tags[1],
                note="I approve this place!"
            ),
            PlaceTag.objects.create(
                place=self.place,
                tag=self.tags[2],
                note="I reject this place!",
            )
        ]

        self.origin = Origin.objects.create(pattern='def', dataset=self.dataset)
        Origin.objects.create(pattern='def2', dataset=self.dataset)

        self.authorized_user = User.objects.create_user(
            username='temp_user2',
            password='lkjasdf'
        )
        group = Group.objects.create(
            dataset=self.dataset,
            name='mygroup'
        )
        group.submitters.add(self.authorized_user)
        GroupPermission.objects.create(
            group=group,
            # TODO: rename this to 'resource':
            submission_set='tags',
            can_create=True,
        )

        self.unauthorized_user = User.objects.create_user(
            username='temp_user',
            password='lkjasdf'
        )
        unauthorized_group = Group.objects.create(
            dataset=self.dataset,
            name='badgroup'
        )
        unauthorized_group.submitters.add(self.unauthorized_user)
        unauthorized_group.submitters.add(self.authorized_user)
        GroupPermission.objects.create(
            group=unauthorized_group,
            # TODO: rename this to 'resource':
            submission_set='tags',
        )
        self.other_dataset = DataSet.objects.create(slug='ds2', owner=self.owner)

        self.other_tag = Tag.objects.create(
            name="other status",
            dataset=self.other_dataset,
        )

        other_group = Group.objects.create(
            dataset=self.other_dataset,
            name='othergroup'
        )
        other_group.submitters.add(self.authorized_user)
        GroupPermission.objects.create(
            group=other_group,
            # TODO: rename this to 'resource':
            submission_set='tags',
            can_create=True,
        )

        self.request_kwargs = {
          'owner_username': self.owner.username,
          'dataset_slug': self.dataset.slug,
          'place_id': self.place.id,
        }

        self.factory = RequestFactory()
        self.path = reverse('place-tag-list', kwargs=self.request_kwargs)
        self.view = PlaceTagListView.as_view()

    def tearDown(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        # this should delete all PlaceTags:
        Place.objects.all().delete()
        Tag.objects.all().delete()

        cache_buffer.reset()
        django_cache.clear()

    def test_OPTIONS_response(self):
        request = self.factory.options(self.path)
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

        place_tag = None
        for result in data['results']:
            if result['id'] == self.place_tags[-1].id:
                place_tag = result
        self.assertEqual(place_tag['url'],
                         'http://testserver' + reverse('place-tag-detail', args=[
                             self.owner.username,
                             self.dataset.slug,
                             self.place.id,
                             self.place_tags[-1].id,
                         ]))

    def test_GET_invalid_url(self):
        # Make sure that we respond with 404 if a slug is supplied, but for
        # the wrong dataset or owner.
        request_kwargs = {
          'owner_username': 'mischevious_owner',
          'dataset_slug': self.dataset.slug,
          'place_id': self.place.id,
        }

        path = reverse('place-tag-list', kwargs=request_kwargs)
        request = self.factory.get(path)
        response = self.view(request, **request_kwargs)

        self.assertStatusCode(response, 404)

    def test_POST_response(self):
        tag_url = 'http://testserver' + reverse('tag-detail', args=[
            self.owner.username,
            self.dataset.slug,
            self.tags[1].id,
        ])
        place_url = 'http://testserver' + reverse('place-detail', args=[
            self.owner.username,
            self.dataset.slug,
            self.place.id,
        ])
        data = json.dumps({
          'note': "this is a comment",
          'tag': tag_url,
          'place': place_url,
        })
        start_num_submissions = PlaceTag.objects.all().count()

        #
        # View should 401 when trying to create when not authenticated
        #
        request = self.factory.post(self.path, data=data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should 403 when trying to create when not authorized
        #
        request = self.factory.post(self.path, data=data, content_type='application/json')
        request.user = self.unauthorized_user
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 403)

        #
        # View should create the submission and set when owner is authenticated
        #
        request = self.factory.post(self.path, data=data, content_type='application/json')
        request.user = self.authorized_user
        response = self.view(request, **self.request_kwargs)

        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 201)

        # # Check that the data attributes have been incorporated into the
        # # properties
        self.assertEqual(data.get('note'), 'this is a comment')
        self.assertEqual(data.get('submitter')['username'], 'temp_user2')

        # # visible should be true by default
        # self.assert_(data.get('visible'))

        # Check that we actually created a submission and set
        final_num_submissions = PlaceTag.objects.all().count()
        self.assertEqual(final_num_submissions, start_num_submissions + 1)

    def test_POST_response_with_invalid_tag(self):
        tag_url = 'http://testserver' + reverse('tag-detail', args=[
            self.owner.username,
            self.other_dataset.slug,
            self.other_tag.id,
        ])
        place_url = 'http://testserver' + reverse('place-detail', args=[
            self.owner.username,
            self.dataset.slug,
            self.place.id,
        ])
        data = json.dumps({
          'note': "this is a comment",
          'tag': tag_url,
          'place': place_url,
        })

        #
        # Trying to add a Tag to a Place that comes from a different
        # dataset should give us a ValidationError:
        #
        request = self.factory.post(self.path, data=data, content_type='application/json')
        request.user = self.authorized_user
        with self.assertRaises(ValidationError):
            self.view(request, **self.request_kwargs)
