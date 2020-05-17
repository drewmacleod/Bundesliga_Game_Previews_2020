import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib as plt
import re
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import matplotlib.backends.backend_pdf
import PyPDF2
import os
import sys

class game_preview:
    
    def __init__(self, home_team, away_team, home_df, away_df, form_df, xg_df, narrow_stats, betting_info):
        if home_team not in list(home_df.index):
            print("error not a permitted home team name")
            return
        if away_team not in list(away_df.index):
            print("error not a permitted away team name")
            return
        self.home_team = home_team
        self.away_team = away_team
        self.home_team_avgs = home_df.loc[home_team]
        self.away_team_avgs = away_df.loc[away_team]
        self.matchup = pd.concat([self.away_team_avgs.to_frame().transpose(),self.home_team_avgs.to_frame().transpose()])
        self.form_df = form_df
        self.xg_df = xg_df
        self.narrow_stats = narrow_stats
        self.betting_info = betting_info
        self.home_re = r'.*' + home_team + '.*'
        self.away_re = r'.*' + away_team + '.*'
        self.out_pdf_df= r'/Users/drewmacleod/Documents/Gambling/Bundesliga/Previews/' + self.away_team.replace(' ', '_') + '_at_' + self.home_team.replace(' ', '_') + '_dfs' + '.pdf'
        self.out_pdf_graphs = r'/Users/drewmacleod/Documents/Gambling/Bundesliga/Previews/' + self.away_team.replace(' ', '_') + '_at_' + self.home_team.replace(' ', '_') + '_graphs.pdf'
        self.final_file_name = r'/Users/drewmacleod/Documents/Gambling/Bundesliga/Previews/' + self.away_team.replace(' ', '_') + '_at_' + self.home_team.replace(' ', '_') + '.pdf'
        
        
    def make_teams_graph(self):
        teams_matchup = self.matchup[['Goals Against', 'Goals', 'Shots Against', 'Shots For', 'Shots on Target', 'Shots on Target Allowed', \
                  'Corners', 'Corners Allowed']]
        ax = teams_matchup.transpose().plot(kind='bar', legend=True, grid=True)
        ax.set_title('Team Stats', loc= 'left')
        for p in ax.patches:
            ax.annotate(str(round(p.get_height(),2)), (p.get_x() - p.get_x() * .01, p.get_height() * 1.04))

        return ax
        # make graphical preview with each team and their shots, goals, etc.
        
    def make_betting_graph(self):
        betting_stats = self.matchup[['Half Time Differential', 'Full Time Differential', 'Half Time Total', 'Full Time Total']]
        ax1 = betting_stats.transpose().plot(kind='bar', legend=True, grid=True)
        ax1.set_title('Betting Stats')
        for p in ax1.patches:
            ax1.annotate(str(round(p.get_height(),2)), (p.get_x() + .01, p.get_height() * 1.04))
        return ax1
        # have averages for each team totals on home and away and then the league average
        
    def make_form_info(self):
        form_df = self.form_df[['Squad','W','D','L', 'Pts', 'Last 5', 'xGDiff/90']]
        return form_df[(form_df['Squad'] == self.home_team) | (form_df['Squad'] == self.away_team)]
        
    def head_to_head_info(self):
        h2h = self.narrow_stats[((self.narrow_stats['HomeTeam'] == self.home_team) & (self.narrow_stats['AwayTeam'] == self.away_team))|
             ((self.narrow_stats['HomeTeam'] == self.away_team) & (self.narrow_stats['AwayTeam'] == self.home_team))]
        h2h = h2h[['Date','HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']]
        h2h.columns = ['Date','HomeTeam', 'AwayTeam', 'Home Score', 'Away Score', 'Result']
        if h2h.empty:
            return 'No previous matchups or team name error'
        return h2h
            # maybe make to show recent head to head matchups
    def home_away_splits(self):
        xg_df = self.xg_df.set_index('Unnamed: 1_level_0',     'Squad').reset_index()
        xg_df['Squad'] = xg_df['Unnamed: 1_level_0'].apply(tuple_to_string)
        xg_df = xg_df.set_index('Squad')
        xg_df = xg_df.drop(['Unnamed: 1_level_0'],axis=1)
        non_matchup_squads = list(xg_df.index)
        non_matchup_squads.remove(self.home_team)
        non_matchup_squads.remove(self.away_team)
        xg_df = xg_df.drop(non_matchup_squads)
        xg_df = xg_df.drop([(              'Home',     'Pts/G'),
            (              'Home',        'xG'),
            (              'Home',       'xGA'),
            (              'Home',    'xGDiff'),
            (              'Away',     'Pts/G'),
            (              'Away',        'xG'),
            (              'Away',       'xGA'),
            (              'Away',    'xGDiff'),], axis=1)
        return xg_df

    def get_current_lines(self):
        """
            This function will return a tuple with the spread of the matchup in a dataframe as the first object.
             And the totals for the matchup as a datframe as the second object.
        """
        home_re = self.home_re
        away_re = self.away_re
        spread_df = pd.DataFrame()
        total_odds_df = pd.DataFrame()
        for game in self.betting_info:
            counter = 1
            away = None
            home = None
            over = None
            over_dic = None
            for row in game:
                team = row.get("team", None)
                type_bet = row.get("type", None)
                if team and re.match(home_re, team) and counter ==1:
                    counter = 2
                    home = team  
                    home_spread = row['spread']
                    home_spread2 = row.get('spread2', None)
                    home_odds = row['odds']
                # this has info on away team bets
                elif team and re.match(away_re,team) and counter==2:
                    counter = 3
                    temp_lst = list()
                    home_dic = {'team': home,
                            'spread': home_spread,
                            'spread2': home_spread2,
                            'odds': home_odds}
                    away_dic = {'team': team,
                            'spread': row['spread'],
                            'spread2': row.get('spread2', None),
                            'odds': row['odds']}
                    temp_lst.append(home_dic)
                    temp_lst.append(away_dic)
                    spread_df = pd.DataFrame(temp_lst).set_index('team')
                    # this has info on home team bets
                elif counter==3:
                    over_dic = {'type': type_bet,
                            'total': row['total'],
                            'total2': row.get('total2', None),
                            'odds': row['odds']}
                    counter=4
                
                # this will have info on over for the right game
                elif counter == 4:
                    counter = 5
                    temp_lst = list()
                    under = type_bet
                    total = row['total']
                    total2 = row.get('total2', None)
                    under_odds = row['odds']
                    under_dic = { 'type': under,
                              'total': total,
                              'total2': total2,
                              'odds': under_odds}
                    temp_lst.append(over_dic)
                    temp_lst.append(under_dic)
                    total_odds_df = pd.DataFrame(temp_lst).set_index('type')
                    # this will have info on under for the right game
                elif counter == 5:
                    # money line odds for home team
                    counter = 6
                    home_ml = {
                        'team': team,
                        'odds_ml': row['ml_odds']
                    }
                elif counter == 6:
                    # money line odds for away team
                    counter = 7
                    away_ml = {
                        'team': team,
                        'odds_ml': row['ml_odds']
                    }
                elif counter == 7:
                    temp_lst = list()
                    # Draw money line odds
                    draw_ml = {
                        'team': team,
                        'odds_ml': row['ml_odds']
                    }
                    temp_lst.append(home_ml)
                    temp_lst.append(away_ml)
                    temp_lst.append(draw_ml)
                    temp_df = pd.DataFrame(temp_lst).set_index('team')
                    spread_df = spread_df.merge(temp_df, left_index=True, right_index=True, how='outer')
                    spread_df = spread_df.fillna('-')

        return (spread_df, total_odds_df)
        
    def get_df_pdf(self):
        # get necessary data frames
        game_matchup_odds = self.get_current_lines()[0]
        total_odds = self.get_current_lines()[1]
        if game_matchup_odds.empty:
            print("Check home and away teams, no current lines for selected teams")
            sys.exit()
        teams_form_df = self.make_form_info()
        h2h_df = self.head_to_head_info()
        home_away_df = self.home_away_splits()
        # make temporary file to hold all dfs
        pdf_title = self.away_team + ' at ' + self.home_team + " Preview"
        template_vars = {"title": pdf_title,
                 "game_matchup_odds": game_matchup_odds.to_html(),
                 "total_odds": total_odds.to_html(),
                 "home_away_df": home_away_df.to_html(),
                 "h2h_df": h2h_df.to_html(),
                 "form_df": teams_form_df.to_html()}
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("Previews/templates/df_template.html")
        html_out = template.render(template_vars)
        HTML(string=html_out).write_pdf(self.out_pdf_df)
        return

    def get_graphs_pdf(self):
        pdf = matplotlib.backends.backend_pdf.PdfPages(self.out_pdf_graphs)
        fig2 = self.make_betting_graph().figure
        fig1 = self.make_teams_graph().figure
        fig1.tight_layout()
        pdf.savefig(fig1)
        fig2.tight_layout()
        pdf.savefig(fig2)
        pdf.close()
        return

    def combine_pdfs(self):
        pdf1File = open(self.out_pdf_df, 'rb')
        pdf2File = open(self.out_pdf_graphs, 'rb')
        pdf1Reader = PyPDF2.PdfFileReader(pdf1File)
        pdf2Reader = PyPDF2.PdfFileReader(pdf2File)
        pdfWriter = PyPDF2.PdfFileWriter()
        # Loop through all the pagenumbers for the first document
        for pageNum in range(pdf1Reader.numPages):
            pageObj = pdf1Reader.getPage(pageNum)
            pdfWriter.addPage(pageObj)

        for pageNum in range(pdf2Reader.numPages):
            pageObj = pdf2Reader.getPage(pageNum)
            pdfWriter.addPage(pageObj)

        # Now that you have copied all the pages in both the documents, write them into the a new document
        pdfOutputFile = open(self.final_file_name, 'wb')
        pdfWriter.write(pdfOutputFile)
 
        # Close all the files - Created as well as opened
        pdfOutputFile.close()
        pdf1File.close()
        pdf2File.close()
        # delete temporary df and graphs files
        os.remove(self.out_pdf_df)
        os.remove(self.out_pdf_graphs)
        return

    def get_preview(self):
        self.get_df_pdf()
        self.get_graphs_pdf()
        self.combine_pdfs()

        return

    def __str__(self):
        return("Game Preview of " + self.away_team + " at " + self.home_team)

def tuple_to_string(tup):
        return tup[0]
