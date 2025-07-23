from src.snuffelfiets import routefilter as rf

df = rf.read_data()
dfR_list, routes = rf.read_routes()
rf.filter_routes(dfR_list, routes, df)