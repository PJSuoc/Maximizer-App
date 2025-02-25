DROP TABLE IF EXISTS ballot_initiatives;

CREATE TABLE ballot_initiatives (

    name varchar(60),
    party varchar(60),
    state_name varchar(30),
    state varchar(4),
    congress varchar(4),
    s_upper varchar(4),
    s_lower varchar(4),
    race_type varchar(30),
    election_name varchar(60),
    initiative_name varchar(60),
    initiative_type varchar(60),
    info_link varchar(100),
    supporting_org_link varchar(100),
    categorical_flag varchar(60),
    numerical_flag int,
    explainer_text varchar(500),
    PRIMARY KEY (state, congress, s_upper, s_lower, initiative_name)
);