from os import environ

SESSION_CONFIGS = [
    dict(
        name='Twitter',
        app_sequence=['DICE'],
        num_demo_participants=3,
        channel_type="Twitter", # "Twitter_Replies",
    ),
    dict(
        name='Instagram',
        app_sequence=['DICE'],
        num_demo_participants=3,
        channel_type="Insta",
    ),
    dict(
        name='Stories',
        app_sequence=['DICE'],
        num_demo_participants=3,
        channel_type="Stories",
        story_duration=7,  # seconds each story is displayed before auto-advancing
    ),
    dict(
        name='Linkedin',
        app_sequence=['DICE'],
        num_demo_participants=3,
        channel_type="Linkedin",
    ),
    dict(
        name='Generic',
        app_sequence=['DICE'],
        num_demo_participants=3,
        channel_type="Generic",
    ),
    dict(
        name='InstagramInternalQuestionnaire',
        app_sequence=['DICE'],
        num_demo_participants=1,
        journey_steps=[
            dict(
                step_id="feed_1",
                channel_type="Insta",
                questionnaire_mode="internal",
                questionnaire_id="feed_1_followup",
                questionnaire_questions=[
                    dict(
                        question_id="enjoyment",
                        prompt="How much did you enjoy this feed?",
                        question_type="likert",
                        likert_min=1,
                        likert_max=5,
                        likert_min_label="Not at all",
                        likert_max_label="Very much",
                    ),
                    dict(
                        question_id="recalled_posts",
                        prompt="Which topics do you remember from the posts you just saw?",
                        question_type="multiple_choice",
                        is_required=False,
                        options=[
                            dict(value="travel", label="Travel"),
                            dict(value="food", label="Food"),
                            dict(value="fitness", label="Fitness"),
                            dict(value="none", label="None of these"),
                        ],
                    ),
                    dict(
                        question_id="first_impression",
                        prompt="What are your first thoughts about this feed?",
                        question_type="open_text",
                        is_required=False,
                    ),
                ],
            ),
            dict(
                step_id="feed_2",
                channel_type="Insta",
                questionnaire_mode="internal",
                questionnaire_id="feed_2_followup",
                questionnaire_questions=[
                    dict(
                        question_id="enjoyment",
                        prompt="How much did you enjoy this second feed?",
                        question_type="likert",
                        likert_min=1,
                        likert_max=5,
                        likert_min_label="Not at all",
                        likert_max_label="Very much",
                    ),
                    dict(
                        question_id="preferred_feed",
                        prompt="Compared to the first feed, which did you prefer?",
                        question_type="single_choice",
                        options=[
                            dict(value="feed_1", label="The first feed"),
                            dict(value="feed_2", label="This feed"),
                            dict(value="no_preference", label="No preference"),
                        ],
                    ),
                ],
            ),
        ],
    ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0,
    title = '',
    full_name = '',
    eMail = '',
    study_name = 'A study about social media',
    channel_type = 'Twitter',
    survey_link = 'https://unisg.qualtrics.com/jfe/form/SV_0DnMoLpM0VxjhrM',
    journey_steps = [],
    max_journey_steps = 20,
    return_param_name = 'return_url',
    bridge_redirect_delay_ms = 1200,
    default_return_strategy = 'auto_or_manual',
    dwell_threshold = 75,
    story_duration = 7,
    url_param = 'PROLIFIC_PID',
    skip_intro = False,
    skip_briefing = False,
    briefing = '', # '<h5>This could be your briefing</h5><p>Use HTML syntax to format your content to your liking.</p>',
    consent_form = '',
    data_path=  "https://raw.githubusercontent.com/DICE-app/sample-feeds/refs/heads/main/feeds/sample_2x2_brand_safety.csv", #'DICE/static/data/sample_tweets.csv', #'DICE/static/data/9gag.csv', #  "https://raw.githubusercontent.com/Howquez/DICE/main/studies/frequency_capping/stimuli/brazil_pretest.csv",
    delimiter=';',
    sort_by='datetime',
    condition_col='condition',
    search_term = "@9GAG", #"'#Yosemite',

    # Legacy ?
    topics = True,
    # copy_text = '50M Jobseekers. <br><br> 150+ Job Boards. <br><br> One Click.',
    copy_text= '', # 'Happy<br>National<br>Fried Chicken<br>Day!',
    show_cta = False,
    cta_text = '', # 'Post Jobs Free',
    # landing_page = 'https://unisg.qualtrics.com/jfe/form/SV_0DnMoLpM0VxjhrM',

)

PARTICIPANT_FIELDS = [
    'tweets',
    'finished',
    'journey_steps_resolved',
    'journey_current_step',
    'journey_completed_steps',
    'journey_step_tokens',
]
SESSION_FIELDS = ['prolific_completion_url', 'completion_code']

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = False

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ Welcome """

SECRET_KEY = '8744261096089'
