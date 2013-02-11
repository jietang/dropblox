select sub.team_name, team_members.email, sub.max_competition_score
from (
     select teams.team_name, teams.tournament_id,
     	    max(case competition.is_practice when 0 then game.score else 0 end) as max_competition_score
     from teams
     left join game on teams.id = game.team_id
     left join competition on game.competition_id = competition.id
     group by teams.id
     ) as sub
join team_members on sub.team_name = team_members.team_name and sub.tournament_id = team_members.tournament_id
order by max_competition_score desc, team_name;
