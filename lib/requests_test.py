import requests,time
data = {"type":"hum","value":100}
response = requests.post("http://student.gml.cz/skriptsql.php",json=data)
while response.text == "":
    pass
print(response.text)