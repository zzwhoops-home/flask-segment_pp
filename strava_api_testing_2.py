import mysql.connector
from mysql.connector.constants import ClientFlag

# configuration for sql database connection
config = {
}
# establishing connection
config['database'] = 'segment_pp_database'  # add new database to config dict
sql_connection = mysql.connector.connect(**config)
cursor = sql_connection.cursor()

cursor.execute("SELECT * FROM access_tokens WHERE id = %s", (31849223,))
result = cursor.fetchall()
print (result)

cursor.execute("SELECT * FROM refresh_tokens WHERE id = %s", (31849223,))
result = cursor.fetchall()
print (result)


sql_connection.close()


# table creation (one-time)
"""
cursor.execute("CREATE TABLE access_tokens (id INT PRIMARY KEY, scope BOOLEAN, a_token VARCHAR(255), expires_at INT)")
cursor.execute("CREATE TABLE refresh_tokens (id INT PRIMARY KEY, r_token VARCHAR(255), scope BOOLEAN)")
"""

# select based on program variable
# cursor.execute("SELECT * FROM access_tokens WHERE id = %s", (31849223,))

# delete data
"""
cursor.execute("TRUNCATE TABLE access_tokens")
cursor.execute("TRUNCATE TABLE refresh_tokens")
"""
# add columns
"""
cursor.execute("ALTER TABLE access_tokens ADD COLUMN epoch_join INT")
cursor.execute("ALTER TABLE refresh_tokens ADD COLUMN epoch_join INT")
"""