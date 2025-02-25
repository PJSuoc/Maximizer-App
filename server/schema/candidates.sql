DROP TABLE IF EXISTS candidates;

CREATE TABLE candidates (

    name varchar(60),
    party varchar(60),
    state_name varchar(30),
    state varchar(4),
    congress varchar(4),
    s_upper varchar(4),
    s_lower varchar(4),
    race_type varchar(30),
    election_name varchar(60),
    denier_flag boolean,
    campaign_link varchar(100),
    donate_link varchar(100),
    contact_link varchar(100)
);

INSERT INTO candidates (name, party, state_name, state, congress, s_upper, s_lower, race_type,
                        election_name, denier_flag, campaign_link, donate_link, contact_link)
SELECT  cand1_name, cand1_party, state_name, state, congress, s_upper, s_lower, race_type,
        election_name, cand1_denier, cand1_campaign, cand1_donate, cand1_contact FROM input_elections;

INSERT INTO candidates (name, party, state_name, state, congress, s_upper, s_lower, race_type,
                        election_name, denier_flag, campaign_link, donate_link, contact_link)
SELECT  cand2_name, cand2_party, state_name, state, congress, s_upper, s_lower, race_type,
        election_name, cand2_denier, cand2_campaign, cand2_donate, cand2_contact FROM input_elections;

INSERT INTO candidates (name, party, state_name, state, congress, s_upper, s_lower, race_type,
                        election_name, denier_flag, campaign_link, donate_link, contact_link)
SELECT  cand3_name, cand3_party, state_name, state, congress, s_upper, s_lower, race_type,
        election_name, cand1_denier, cand3_campaign, cand3_donate, cand3_contact FROM input_elections;

INSERT INTO candidates (name, party, state_name, state, congress, s_upper, s_lower, race_type,
                        election_name, denier_flag, campaign_link, donate_link, contact_link)
SELECT  cand4_name, cand4_party, state_name, state, congress, s_upper, s_lower, race_type,
        election_name, cand4_denier, cand4_campaign, cand4_donate, cand4_contact FROM input_elections;

INSERT INTO candidates (name, party, state_name, state, congress, s_upper, s_lower, race_type,
                        election_name, denier_flag, campaign_link, donate_link, contact_link)
SELECT  cand5_name, cand5_party, state_name, state, congress, s_upper, s_lower, race_type,
        election_name, cand5_denier, cand5_campaign, cand5_donate, cand5_contact FROM input_elections;

INSERT INTO candidates (name, party, state_name, state, congress, s_upper, s_lower, race_type,
                        election_name, denier_flag, campaign_link, donate_link, contact_link)
SELECT  cand6_name, cand6_party, state_name, state, congress, s_upper, s_lower, race_type,
        election_name, cand6_denier, cand6_campaign, cand6_donate, cand6_contact FROM input_elections;
