import mysql.connector
from mysql.connector.constants import ClientFlag

# configuration for sql database connection
config = {
}
# establishing connection
config['database'] = 'segment_pp_database'  # add new database to config dict
sql_connection = mysql.connector.connect(**config)
cursor = sql_connection.cursor(dictionary=True)
"""
cursor.execute("SELECT * FROM access_tokens WHERE id = %s", (31849223,))
result = cursor.fetchall()
print (result)

cursor.execute("SELECT * FROM refresh_tokens WHERE id = %s", (31849223,))
result = cursor.fetchall()
print (result)

cursor.execute("SELECT * FROM athlete_info WHERE id = %s", (31849223,))
result = cursor.fetchall()
print (result)
"""

cursor.execute("SELECT a_token, expires_at FROM access_tokens WHERE id = %s", (31849223,))
result = cursor.fetchall()[0]
print(result)
cursor.execute("SELECT r_token FROM refresh_tokens WHERE id = %s", (31849223,))
result = cursor.fetchall()[0]
print(result)

"""
cursor.execute("UPDATE refresh_tokens SET r_token = %s", ('wheofy43423dfgfgergoui3',))
sql_connection.commit()
"""
sql_connection.close()


# table creation (one-time)
"""
cursor.execute("CREATE TABLE access_tokens (id INT PRIMARY KEY, scope BOOLEAN, a_token VARCHAR(255), expires_at INT)")
cursor.execute("CREATE TABLE refresh_tokens (id INT PRIMARY KEY, r_token VARCHAR(255), scope BOOLEAN)")
cursor.execute("CREATE TABLE athlete_info (id INT PRIMARY KEY, username VARCHAR(255), firstname VARCHAR(255), lastname VARCHAR(255), city VARCHAR(255), state VARCHAR(255), country VARCHAR(255), sex VARCHAR(1), avatar VARCHAR(255), epoch_join INT)")
"""

# select based on program variable
# cursor.execute("SELECT * FROM access_tokens WHERE id = %s", (31849223,))

# delete data
"""
cursor.execute("TRUNCATE TABLE access_tokens")
cursor.execute("TRUNCATE TABLE refresh_tokens")
cursor.execute("TRUNCATE TABLE athlete_info")
"""
# add columns
"""
cursor.execute("ALTER TABLE access_tokens ADD COLUMN epoch_join INT")
cursor.execute("ALTER TABLE refresh_tokens ADD COLUMN epoch_join INT")
"""