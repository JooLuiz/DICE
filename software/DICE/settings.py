from os import environ

from session_config_steps import MAX_CONFIGURABLE_JOURNEY_STEPS

SESSION_CONFIGS = [
    dict(
        name='Twitter',
        app_sequence=['DICE'],
        num_demo_participants=3,
        channel_type="Twitter",
    ),
    dict(
        name='Instagram',
        app_sequence=['DICE'],
        num_demo_participants=1,
        channel_type="Insta",
        # journey_steps is intentionally left unset here: when creating a real session from
        # /sessions, the step_N_* fields (filled in on that page, via the "Journey Steps" UI
        # section) are assembled into journey_steps automatically by
        # session_config_steps.build_steps_from_numbered_fields.
        # See the "Running a Real Study Without Editing Code" section in README.md.
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
    survey_link = '',  # legacy single-step fallback; configure per step via Journey Steps instead
    completion_redirect_url = '',  # optional; shown as a button on the final debrief page
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
    data_path='',  # legacy single-step fallback; configure per step via Journey Steps instead
    delimiter=';',
    sort_by='datetime',
    condition_col='condition',
    search_term = "@9GAG", #"'#Yosemite',
    language = 'pt-br',  # 'en' — translates fixed UI; set briefing/consent_form/study_name/CSV in target language

    # Legacy ?
    topics = True,
    # copy_text = '50M Jobseekers. <br><br> 150+ Job Boards. <br><br> One Click.',
    copy_text= '', # 'Happy<br>National<br>Fried Chicken<br>Day!',
    show_cta = False,
    cta_text = '', # 'Post Jobs Free',
    # landing_page = 'https://unisg.qualtrics.com/jfe/form/SV_0DnMoLpM0VxjhrM',

    # Numbered journey step slots, editable on the /sessions create-session page for every
    # config via the "Journey Steps" UI section. A slot is used when it has a feed CSV, a
    # survey link, or a questionnaire JSON; a slot with all three blank is skipped.
    # See session_config_steps.py and the "Running a Real Study Without Editing Code" section
    # in README.md.
    **{
        f"step_{slot_index}_{suffix}": ""
        for slot_index in range(1, MAX_CONFIGURABLE_JOURNEY_STEPS + 1)
        for suffix in ("feed_csv_url", "survey_link", "questionnaire_json")
    },
)

PARTICIPANT_FIELDS = [
    'finished',
    'journey_steps_resolved',
    'journey_current_step',
    'journey_completed_steps',
    'journey_step_tokens',
]

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
