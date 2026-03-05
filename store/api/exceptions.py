from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException

class PriceTooLowException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Price must be greater than 10'
    default_code = 'invalid_price'

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return Response({
            "status": "error",
            "message": response.data,
            "status_code": response.status_code
        }, status=response.status_code)

    return Response({
        "status": "error",
        "message": "Internal server error",
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)