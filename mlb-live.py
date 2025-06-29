import requests
import pprint
import pytz
from datetime import datetime, timezone, timedelta

gmt = pytz.timezone('GMT')
eastern = pytz.timezone("US/Eastern")

# Define function to return stats for a pitcher given their ID
def pitcher_stats(pitcher_id):
    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats?stats=season&group=pitching"
    response = requests.get(url)
    data = response.json()
    stats = data['stats'][0]['splits'][0]['stat']
    stats['name'] = data['stats'][0]['splits'][0]['player']['fullName']
    try:
        stats['team'] = data['stats'][0]['splits'][0]['team']['name']
    except:
        stats['team'] = data['stats'][0]['splits'][1]['team']['name']
    return(stats)

# Pull today's games from API
today = datetime.now().astimezone(eastern).strftime('%Y-%m-%d')

url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher(note,stats,person),decisions&language=en"
response = requests.get(url)
data = response.json()

games = data['dates'][0]['games']
game_ids = [game['gamePk'] for game in games]

time_left = (datetime.strptime(games[0]['gameDate'],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) - datetime.now(timezone.utc))
year = datetime.now().year

# Create HTML file
f = open('index.html', 'w')
f.write(f"""
<html>
<head>
<title>MLB Live Scoreboard: {today}</title>
<link rel="stylesheet" href="bootstrap.css">
<link rel="icon" type="image/x-icon" href="favicon.ico"     
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="author" content="Ari Levin">
</head>
<body>
""")


if time_left.days < 0:
    f.write("<h1>Baseball has started!</h1>\n")
else:
    hours = time_left.seconds // 3600
    minutes = (time_left.seconds % 3600) // 60
    seconds = (time_left.seconds % 60)
    f.write(f"<h1>Baseball starts in {hours} hours, {minutes} minutes and {seconds} seconds</h1>\n")
f.write("<p><em>All times Eastern</em></p>")

# Get team streaks
streaks = {}
url = f"https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season={year}&type=regularSeason"
response = requests.get(url)
data = response.json()   
for division in data['records']:
    for team in division['teamRecords']:
        streaks[team['team']['id']] = team['streak']['streakCode']

# Write games to HTML file
game_ids = [game['gamePk'] for game in games]
for game in games:
    f.write("<div>\n")
    game_id = game['gamePk']
    teams = game['teams']
    away_team = teams['away']['team']['name']
    home_team = teams['home']['team']['name']
    away_id = teams['away']['team']['id']
    home_id = teams['home']['team']['id']
    try:
        home_pitcher_name = teams['home']['probablePitcher']['fullName']
    except:
        home_pitcher_name = "TBD"
    try:
        home_pitcher_stats = pitcher_stats(teams['home']['probablePitcher']['id'])
    except:
        home_pitcher_stats = {}
    try:
        away_pitcher_name = teams['away']['probablePitcher']['fullName']
    except:
        away_pitcher_name = "TBD"
    try:
        away_pitcher_stats = pitcher_stats(teams['away']['probablePitcher']['id'])
    except:
        away_pitcher_stats = {}
    home_record = game['teams']['home']['leagueRecord']
    away_record = game['teams']['away']['leagueRecord']
    game_time = datetime.strptime(game['gameDate'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tz=None)
    game_time = game_time.astimezone(eastern)
# For games that have not yet started
    if game['status']['abstractGameState'] == 'Preview' or game['status']['detailedState'] == 'Warmup':
        f.write(f"<h2>{game_time.strftime('%I:%M %p')}</h2>\n")
        try:
            f.write(f"<p>{away_team} ({away_record['wins']}-{away_record['losses']}, {streaks[away_id]}) -- {away_pitcher_name} ({away_pitcher_stats['wins']}-{away_pitcher_stats['losses']}, {away_pitcher_stats['era']} ERA)<br>\n")
        except:
            f.write(f"<p>{away_team} ({away_record['wins']}-{away_record['losses']}, {streaks[away_id]}) -- {away_pitcher_name}<br>\n")
        f.write("vs.<br>\n")
        try:
            f.write(f"{home_team} ({home_record['wins']}-{home_record['losses']}, {streaks[home_id]}) -- {home_pitcher_name} ({home_pitcher_stats['wins']}-{home_pitcher_stats['losses']}, {home_pitcher_stats['era']} ERA)</p>\n")
        except:
            f.write(f"{home_team} ({home_record['wins']}-{home_record['losses']}, {streaks[home_id]}) -- {home_pitcher_name}</p>\n")
    
    elif game['status']['abstractGameState'] == 'Live':
        url = f"https://statsapi.mlb.com/{game['link']}"
        response = requests.get(url)
        data = response.json()

        home_score = game['teams']['home']['score']
        away_score = game['teams']['away']['score']
        inning = f"{data['liveData']['linescore']['inningHalf']} {data['liveData']['linescore']['currentInningOrdinal']}"
        f.write(f"<h2>{inning}:</h2>\n")
        f.write(f"<h5>{away_team} {away_score}, {home_team} {home_score}</h5>\n")
        f.write(f"<p>{data['liveData']['plays']['currentPlay']['matchup']['pitcher']['fullName']} pitching to {data['liveData']['plays']['currentPlay']['matchup']['batter']['fullName']}.<br>\n")
        try:
            f.write(f"{data['liveData']['plays']['currentPlay']['result']['description']}<br>\n")
            try:
                f.write(f"Exit Velocity: {data['liveData']['plays']['currentPlay']['playEvents'][-1]['hitData']['launchSpeed']} MPH<br>\n")
            except: pass
        except:
            try:
                f.write(f"{data['liveData']['plays']['allPlays'][-2]['result']['description']}<br>\n")
            except:
                f.write("Start of game<br>\n")
            try:
                f.write(f"Exit Velocity: {data['liveData']['plays']['allPlays'][-2]['playEvents'][-1]['hitData']['launchSpeed']} MPH<br>\n")
            except: pass
                
        url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/winProbability"
        response = requests.get(url)
        data = response.json()
        probability = round(data[-1]['homeTeamWinProbability'],1)
        if probability < 50:
            f.write(f"The {away_team} have a {100-probability}% chance of winning.</p>\n")
        else:
            f.write(f"The {home_team} have a {probability}% chance of winning.</p>\n")

    elif game['status']['abstractGameState'] == 'Final':
        home_score = game['teams']['home']['score']
        away_score = game['teams']['away']['score']
        f.write("<h2>Final</h2>\n")
        f.write(f"<p>{away_team}: {away_score} | {away_record['wins']}-{away_record['losses']}, {streaks[away_id]}<br>\n")
        f.write(f"{home_team}: {home_score} | {home_record['wins']}-{home_record['losses']}, {streaks[home_id]}</p>\n")

        url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/content"
        response = requests.get(url)
        data = response.json()
        try:
            slug = data['editorial']['recap']['mlb']['slug']
            url = f"https://www.mlb.com/news/{slug}"
            headline = data['editorial']['recap']['mlb']['headline']
            f.write(f"<p><a href={url} target = 'new'>{headline}</a></p>\n")
        except: pass
        try:
            video = data['highlights']['highlights']['items'][0]['playbacks'][0]['url']
            videotitle = data['highlights']['highlights']['items'][0]['headline']
            f.write(f"<video width='480' height='270' controls>\n<source src=\"{video}\">\n")
            f.write(f"<a href={video} target='new'>{videotitle}</a>\n")
            f.write(f"</video>\n<br>\n")
        except: pass
            
        try:
            wp = game['decisions']['winner']['fullName']
            lp = game['decisions']['loser']['fullName']
            try:
                sv = game['decisions']['save']['fullName']
                f.write(f"<p>W: {wp} || L: {lp} || SV: {sv}</p>\n")
            except:
                f.write(f"<p>W: {wp} || L: {lp}</p>\n")
        except: pass

        url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
        response = requests.get(url)
        data = response.json()
        for player in data['topPerformers']:
            name = player['player']['person']['fullName']
            try:
                stats = player['player']['stats']['pitching']['summary']
            except: 
                stats = player['player']['stats']['batting']['summary']    
            f.write(f"<p>{name}: {stats}</p>\n")
        
    f.write("</div>\n")


# Close HTML file
f.write("""
</body>
</html>
""")
f.close()