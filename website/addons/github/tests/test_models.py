import mock
from nose.tools import *
import json

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory

from website.addons.base import AddonError


class TestCallbacks(DbTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()

        self.project = ProjectFactory.build()
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            user=self.project.creator,
        )
        self.project.save()

        self.project.add_addon('github')
        self.project.creator.add_addon('github')
        self.node_settings = self.project.get_addon('github')
        self.user_settings = self.project.creator.get_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_before_page_load_osf_public_gh_public(self, mock_repo):
        self.project.is_public = True
        self.project.save()
        mock_repo.return_value = {'private': False}
        message = self.node_settings.before_page_load(self.project)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_false(message)

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_before_page_load_osf_public_gh_private(self, mock_repo):
        self.project.is_public = True
        self.project.save()
        mock_repo.return_value = {'private': True}
        message = self.node_settings.before_page_load(self.project)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_true(message)

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_before_page_load_osf_private_gh_public(self, mock_repo):
        mock_repo.return_value = {'private': False}
        message = self.node_settings.before_page_load(self.project)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_true(message)

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_before_page_load_osf_private_gh_private(self, mock_repo):
        mock_repo.return_value = {'private': True}
        message = self.node_settings.before_page_load(self.project)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_false(message)

    def test_before_remove_contributor_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.project.creator
        )
        assert_true(message)

    def test_before_remove_contributor_not_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.non_authenticator
        )
        assert_false(message)

    def test_after_remove_contributor_authenticator(self):
        self.node_settings.after_remove_contributor(
            self.project, self.project.creator
        )
        assert_equal(
            self.node_settings.user_settings,
            None
        )

    def test_after_remove_contributor_not_authenticator(self):
        self.node_settings.after_remove_contributor(
            self.project, self.non_authenticator
        )
        assert_not_equal(
            self.node_settings.user_settings,
            None,
        )

    @mock.patch('website.addons.github.api.GitHub.set_privacy')
    def test_after_set_permissions_private_authenticated(self, mock_set_privacy):
        mock_set_privacy.return_value = {}
        message = self.node_settings.after_set_permissions(
            self.project, 'private',
        )
        mock_set_privacy.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
            True,
        )
        assert_true(message)
        assert_in('made private', message.lower())

    @mock.patch('website.addons.github.api.GitHub.set_privacy')
    def test_after_set_permissions_public_authenticated(self, mock_set_privacy):
        mock_set_privacy.return_value = {}
        message = self.node_settings.after_set_permissions(
            self.project, 'public'
        )
        mock_set_privacy.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
            False,
        )
        assert_true(message)
        assert_in('made public', message.lower())

    @mock.patch('website.addons.github.api.GitHub.repo')
    @mock.patch('website.addons.github.api.GitHub.set_privacy')
    def test_after_set_permissions_not_authenticated(self, mock_set_privacy, mock_repo):
        mock_set_privacy.return_value = {'errors': ['it broke']}
        mock_repo.return_value = {'private': True}
        message = self.node_settings.after_set_permissions(
            self.project, 'private',
        )
        mock_set_privacy.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
            True,
        )
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_true(message)
        assert_in('could not set privacy', message.lower())

    def test_after_fork_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            self.project, fork, self.project.creator,
        )
        assert_equal(
            self.node_settings.user_settings,
            clone.user_settings,
        )

    def test_after_fork_not_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            self.project, fork, self.non_authenticator,
        )
        assert_equal(
            clone.user_settings,
            None,
        )

    @mock.patch('website.addons.github.api.GitHub.branches')
    def test_after_register(self, mock_branches):
        rv = [
            {
                'name': 'master',
                'commit': {
                    'sha': '6dcb09b5b57875f334f61aebed695e2e4193db5e',
                    'url': 'https://api.github.com/repos/octocat/Hello-World/commits/c5b97d5ae6c19d5c5df71a34c7fbeeda2479ccbc',
                }
            }
        ]
        mock_branches.return_value = rv
        registration = ProjectFactory()
        clone, message = self.node_settings.after_register(
            self.project, registration, self.project.creator,
        )
        mock_branches.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_equal(
            self.node_settings.user,
            clone.user,
        )
        assert_equal(
            self.node_settings.repo,
            clone.repo,
        )
        assert_equal(
            clone.registration_data,
            {'branches': rv},
        )
        assert_equal(
            clone.user_settings,
            self.node_settings.user_settings
        )

    @mock.patch('website.addons.github.api.GitHub.branches')
    def test_after_register_api_fail(self, mock_branches):
        mock_branches.return_value = None
        registration = ProjectFactory()
        with assert_raises(AddonError):
            self.node_settings.after_register(
                self.project, registration, self.project.creator,
            )
        mock_branches.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )

    def test_hook_callback_add_file(self, mock_hooks):
        url = "/project/{0}/github/hook/".format(self.project._id)
        res = self.node_settings.post(
            url,
            json.dumps(
                {"commits":[{"id":"b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                             "distinct":True,
                             "message":"Updated via the Open Science Framework",
                             "timestamp":"2014-01-08T14:15:51-08:00",
                             "url":"https://github.com/chennan47/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                             "author":{"name":"Illidan","email":"njqpw@osf.io"},
                             "committer":{"name":"Nan Chen","email":"nc6r@virginia.edu","username":"chennan47"},
                             "added":["PRJWN3TV"],"removed":[],"modified":[]}]},
                content_type="application/json")).maybe_follow()
        assert_equal(self.project.logs[-1].action, "file_added")

    def test_hook_callback_modify_file(self, mock_hooks):
        url = "/project/{0}/github/hook/".format(self.project._id)
        res = self.node_settings.post(
            url,
            json.dumps(
                {"commits":[{"id":"b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                             "distinct":True,
                             "message":"Updated via the Open Science Framework",
                             "timestamp":"2014-01-08T14:15:51-08:00",
                             "url":"https://github.com/chennan47/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                             "author":{"name":"Illidan","email":"njqpw@osf.io"},
                             "committer":{"name":"Nan Chen","email":"nc6r@virginia.edu","username":"chennan47"},
                             "added":[],"removed":[],"modified":["PRJWN3TV"]}]},
                content_type="application/json")).maybe_follow()
        assert_equal(self.project.logs[-1].action, "file_modified")

    def test_hook_callback_remove_file(self, mock_hooks):
        url = "/project/{0}/github/hook/".format(self.project._id)
        res = self.node_settings.post(
            url,
            json.dumps(
                {"commits":[{"id":"b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                             "distinct":True,
                             "message":"Updated via the Open Science Framework",
                             "timestamp":"2014-01-08T14:15:51-08:00",
                             "url":"https://github.com/chennan47/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                             "author":{"name":"Illidan","email":"njqpw@osf.io"},
                             "committer":{"name":"Nan Chen","email":"nc6r@virginia.edu","username":"chennan47"},
                             "added":[],"removed":["PRJWN3TV"],"modified":[]}]},
                content_type="application/json")).maybe_follow()
        assert_equal(self.project.logs[-1].action, "file_removed")