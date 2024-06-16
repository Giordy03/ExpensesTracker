# ExpensesTracker

## Web_application
Final project for a communication networks course.

### Overview
The aim of this project is to develop an online budget tracker. This
will be carried on by using `Python` and the packet `Python Flask` for web
development.

### About the project
To construct databases, SQL language was used (in particular SQL Alchemy and
the SQLite Python add-on). The front end is designed primarily using `HTML`;
to make the web page more appealing to the user, basic functions of `CCS`
have been used. 

On the application, each user can add income and expenses. Each transaction 
will be saved with some additional information, so that it will be easy to 
access them. It is possible to visualize all the expenses, and filter among
them (by date or by category). It is possible to add a monthly budget; if it 
has been set, then the user would see the remaining budget and how much he 
should spend on the budget to stay in it at the end of the month.

User information is kept in a database, where the password is hashed using
`Python Bcryipt`. The contents of the `HTTP` messages are not encrypted, though
are sent as clear text. 

All the other date is saved in `JSON` files.


#### University Information 
- **University**: Tongji University, Shanghai
- **Course**: communications networks (bachelor)
- **Department**: Department of computer information technology
- **Semester/Year**: Spring semester 2023-2024 
