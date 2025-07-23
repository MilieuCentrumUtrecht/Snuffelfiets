from src.snuffelfiets import routefilter as rf

df = rf.read_data(years=[2020], months=[1,2,3,4,5,6,7,8,9,10,11,12])
dfR_list, routes = rf.read_routes()
rf.filter_routes(dfR_list, routes, df)