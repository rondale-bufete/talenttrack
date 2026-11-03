from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """?page=2&page_size=50 (capped at 200 so nobody can ask for a million rows)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200
