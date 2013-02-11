create user 'dropblox'@'localhost' identified by 'dropblox';
create database dropblox;
grant all on dropblox.* to 'dropblox'@'localhost' with grant option;
flush privileges;
