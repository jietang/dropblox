use dropblox;
insert ignore into tournament(school_name) values ('hotelroom');
insert ignore into current_tournament(id,tournament_id) values (0,(select id from tournament limit 1));
