"""
.. module:: dj-stripe.tests.test_mixins
   :synopsis: dj-stripe Mixin Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.http.request import HttpRequest
from django.test.client import RequestFactory
from django.test.testcases import TestCase
from mock import patch

from djstripe.mixins import SubscriptionPaymentRequiredMixin, PaymentsContextMixin, SubscriptionMixin
from djstripe.models import Plan
from tests import FAKE_CUSTOMER, FAKE_PLAN, FAKE_PLAN_II


class TestSubscriptionPaymentRequiredMixin(TestCase):

    def setUp(self):
        self.request = HttpRequest()
        self.user = get_user_model().objects.create(username="x", email="user@test.com")
        self.superuser = get_user_model().objects.create(username="y", email="superuser@test.com", is_superuser=True)

    @patch("djstripe.mixins.subscriber_has_active_subscription", return_value=False)
    def test_dispatch_inactive_subscription(self, subscriber_has_active_subscription_mock):
        self.request.user = self.user

        mixin = SubscriptionPaymentRequiredMixin()

        response = mixin.dispatch(self.request)
        self.assertEqual(response.url, reverse("djstripe:subscribe"))

        subscriber_has_active_subscription_mock.assert_called_once_with(self.user)

    @patch("djstripe.mixins.subscriber_has_active_subscription", return_value=True)
    def test_dispatch_active_subscription(self, subscriber_has_active_subscription_mock):
        self.request.user = self.superuser

        mixin = SubscriptionPaymentRequiredMixin()
        self.assertRaises(AttributeError, mixin.dispatch, self.request)


class TestPaymentsContextMixin(TestCase):

    def test_get_context_data(self):
        from django.conf import settings

        class TestSuperView(object):
            def get_context_data(self):
                return {}

        class TestView(PaymentsContextMixin, TestSuperView):
            pass

        context = TestView().get_context_data()
        self.assertIn("STRIPE_PUBLIC_KEY", context, "STRIPE_PUBLIC_KEY missing from context.")
        self.assertEqual(context["STRIPE_PUBLIC_KEY"], settings.STRIPE_PUBLIC_KEY, "Incorrect STRIPE_PUBLIC_KEY.")

        self.assertIn("plans", context, "pans missing from context.")
        self.assertEqual(list(Plan.objects.all()), list(context["plans"]), "Incorrect plans.")


class TestSubscriptionMixin(TestCase):

    def setUp(self):
        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_get_context_data(self, stripe_create_customer_mock):

        class TestSuperView(object):
            def get_context_data(self):
                return {}

        class TestView(SubscriptionMixin, TestSuperView):
            pass

        test_view = TestView()

        test_view.request = RequestFactory()
        test_view.request.user = get_user_model().objects.create(username="x", email="user@test.com")

        context = test_view.get_context_data()
        self.assertIn("is_plans_plural", context, "is_plans_plural missing from context.")
        self.assertTrue(context["is_plans_plural"], "Incorrect is_plans_plural.")

        self.assertIn("customer", context, "customer missing from context.")
