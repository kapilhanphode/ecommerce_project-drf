from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 4
    page_size_query_param = 'page_size'
    max_page_size = 5

    def get_paginated_response(self, data):
        return Response({
            'total_records': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.page_size,
            'next_page': self.get_next_link(),
            'previous_page': self.get_next_link(),
            'results': data
        })

class ProductCursorPagination(CursorPagination):
    page_size = 3
    ordering = '-id'