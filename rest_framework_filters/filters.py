from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils import six

from django_filters.rest_framework.filters import *
from rest_framework_filters.utils import import_class


ALL_LOOKUPS = '__all__'


class AutoFilter(Filter):
    def __init__(self, *args, **kwargs):
        self.lookups = kwargs.pop('lookups', [])

        super(AutoFilter, self).__init__(*args, **kwargs)


class RelatedFilter(AutoFilter, ModelChoiceFilter):
    def __init__(self, filterset, *args, **kwargs):
        self.filterset = filterset
        kwargs.setdefault('lookups', None)

        super(RelatedFilter, self).__init__(*args, **kwargs)

    def filterset():
        def fget(self):
            if isinstance(self._filterset, six.string_types):
                self._filterset = import_class(self._filterset)
            return self._filterset

        def fset(self, value):
            self._filterset = value

        return locals()
    filterset = property(**filterset())

    def get_queryset(self, request):
        queryset = super(RelatedFilter, self).get_queryset(request)
        assert queryset is not None, \
            "Expected `.get_queryset()` for related filter '%s.%s' to return a `QuerySet`, but got `None`." \
            % (self.parent.__class__.__name__, self.name)
        return queryset


class AllLookupsFilter(AutoFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('lookups', ALL_LOOKUPS)
        super(AllLookupsFilter, self).__init__(*args, **kwargs)

class InSetCharFilter(Filter):
    field_class = fields.ArrayCharField

    def __init__(self, *args, **kwargs):
        super(InSetCharFilter, self).__init__(*args, **kwargs)
        warnings.warn(
            'InSetCharFilter is deprecated and no longer necessary. See: '
            'https://github.com/philipn/django-rest-framework-filters/issues/62',
            DeprecationWarning, stacklevel=2
        )


class MethodFilter(Filter):
    """
    This filter will allow you to run a method that exists on the filterset class
    """

    def __init__(self, *args, **kwargs):
        self.action = kwargs.pop('action', '')
        super(MethodFilter, self).__init__(*args, **kwargs)

    def resolve_action(self):
        """
        This method provides a hook for the parent FilterSet to resolve the filter's
        action after initialization. This is necessary, as the filter name may change
        as it's expanded across related filtersets.

        ie, `is_published` might become `post__is_published`.
        """
        # noop if a function was provided as the action
        if callable(self.action):
            return

        # otherwise, action is a string representing an action to be called on
        # the parent FilterSet.
        parent_action = self.action or 'filter_{0}'.format(self.name)

        parent = getattr(self, 'parent', None)
        self.action = getattr(parent, parent_action, None)

        assert callable(self.action), (
            'Expected parent FilterSet `%s.%s` to have a `.%s()` method.' %
            (parent.__class__.__module__, parent.__class__.__name__, parent_action)
        )

    def filter(self, qs, value, *args, **kwargs):
        """
        This filter method will act as a proxy for the actual method we want to
        call.
        It will try to find the method on the parent filterset,
        if not it attempts to search for the method `field_{{attribute_name}}`.
        Otherwise it defaults to just returning the queryset.
        """
        return self.action(self.name, qs, value, self.exclude)
