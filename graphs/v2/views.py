from rest_framework.response import Response
from rest_framework.decorators import api_view
from graphs.v2.serializers import *
from datetime import datetime
import queries

mock_data = {
	'process_type': 17,
	'start': '2018-01-01-08-00-00-000000',
	'end': '2018-01-31-08-00-00-000000',
}

@api_view(['GET'])
def production_actuals(request):
	process_type = request.GET.get('process_type', mock_data['process_type'])
	product_types = request.GET.get('product_types', None)
	start = get_date_from_string(request.GET.get('start', mock_data['start']))
	end = get_date_from_string(request.GET.get('end', mock_data['end']))
	bucketSize = request.GET.get('bucket', 'month')

	queryset = queries.get_output_by_bucket(bucketSize, start, end, process_type, product_types)
	serializer = ProductionActualsSerializer(queryset, many=True)
	return Response(serializer.data)

def get_date_from_string(date):
	dateformat = "%Y-%m-%d-%H-%M-%S-%f"
	return pytz.utc.localize(datetime.strptime(date, dateformat))

