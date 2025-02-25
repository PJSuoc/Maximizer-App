DROP TABLE IF EXISTS elections;

CREATE TABLE elections (

    state_name varchar(30),
    state varchar(4),
    congress varchar(4),
    s_upper varchar(4),
    s_lower varchar(4),
    race_type varchar(30),
    election_name varchar(60),
    voter_power float,
    categorical_flag varchar(60),
    numerical_flag int,
    explainer_text varchar(500),
    PRIMARY KEY (state, congress, s_upper, s_lower, race_type)
);

INSERT INTO elections (state_name, state, congress, s_upper, s_lower, race_type, election_name, 
                       voter_power, categorical_flag, numerical_flag, explainer_text)
SELECT  state_name, state, congress, s_upper, s_lower, race_type, election_name, 
        voter_power, categorical_flag, numerical_flag, explainer_text FROM input_elections;