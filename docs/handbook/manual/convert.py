import subprocess, os
M = dict(home_owner='01-home-owner', home_staff='02-home-staff', requests_list='03-requests-list', request_page_city='04-request-page-with-timeline', review_open='05-decide-page',
 staff_info_form='06-staff-information-form', staff_result='07-staff-result-after-submit', request_page_abn='08-evaluation-cards-with-abn', dashboard='09-dashboard', quick_setup='10-quick-setup',
 doctor='11-doctor', model='12-model-page', customers='13-customers', customer_one='14-customer-page', imports='15-imports', knowledge='16-knowledge', setup='17-setup',
 cp_top='20-controlpanel-top', cp_presets='21-controlpanel-presets', cp_basic='22-controlpanel-basic', cp_review='23-controlpanel-track-record', cp_exceptions='24-controlpanel-exceptions',
 cp_overage='25-controlpanel-small-overage', cp_decline='26-controlpanel-agent-decline', cp_advanced='27-controlpanel-advanced', cp_rules='28-controlpanel-customer-rules',
 cp_schedule='29-controlpanel-scheduled', cp_model='30-controlpanel-team-model', cp_versions='31-controlpanel-versions-counts', nav_more='18-nav-more-open', model_own_decision='19-model-own-decision', model_own_filled='32-model-own-filled', get_started_1='33-get-started-level', get_started_3='34-get-started-display', cp_quick='35-controlpanel-quick-settings')
h = os.path.dirname(os.path.abspath(__file__))
for k, v in M.items():
    subprocess.run(['sips', '--resampleWidth', '1300', '-s', 'format', 'jpeg', '-s', 'formatOptions', '70', f'{h}/raw/{k}.png', '--out', f'{h}/shots/{v}.jpg'], capture_output=True, check=True)
tot = sum(os.path.getsize(f'{h}/shots/{f}') for f in os.listdir(h + '/shots'))
print(len(os.listdir(h + '/shots')), tot / 1e6)
