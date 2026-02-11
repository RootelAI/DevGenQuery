from django.urls import path
from .views import (home, hide_popup, search_help
                  , login_view, logout_view, send_reset_email
                  , register, get_tenants
                  , terms_conditions

                  , master_servers, master_servers_save, master_servers_delete

                  , master_llms, master_llms_save, master_llms_delete
                  , master_llmapis, master_llmapis_save, master_llmapis_delete

                  , master_tenants, master_tenants_save, master_tenants_delete
                  , master_tenant_users, master_tenant_users_save, master_tenant_users_delete
                  , master_tenant_llms, master_tenant_llms_save, master_tenant_llms_delete

                  , master_tenant_request, master_tenant_request_save
                  , master_tenant_request_list, master_tenant_request_list_save

                  , master_projects, master_projects_save, master_projects_delete
                  , master_project_users, master_project_users_save, master_project_users_delete

                  , send_verification_sms, verify_sms_code, check_verification_status, process_sms_verification

                  , master_user_role, master_user_role_save

                  , about_view
                  , service_view
                  , usage_view
                  , qna_view, qna_save, qna_delete, qna_answer_save, qna_answer_delete
                  , faq_view, faq_save, faq_delete
                  , register_qna, register_qna_submit

                  , myinfo, myinfo_update_username, myinfo_update_contact
                  , password_reset

                  , master_tables, master_tables_save, master_tables_delete
                  , master_columns, master_columns_save, master_columns_delete, master_values_save, master_value_delete

                  , master_rag_projects, master_rag_projects_save, master_rag_projects_delete
                  , master_rag_projecttags, master_rag_projecttags_save, master_rag_projecttags_delete

                  , master_rag_files, master_rag_files_save, master_rag_files_delete
                  , master_rag_filemasters, master_rag_filemasters_save, master_rag_filemasters_delete
                    )
                    
# urls.py
urlpatterns = [
    path('', home, name='home'), 

    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path("send-reset-email/", send_reset_email, name="send_reset_email"),
    
    path("register/", register, name="register"),
    path("get_tenants/", get_tenants, name = 'get_tenants'),
    path("terms_conditions/", terms_conditions, name = "terms_conditions"),

    path('master/servers/', master_servers, name = 'master_servers'),
    path('master/servers_save/', master_servers_save, name = 'master_servers_save'),
    path('master/servers_delete/', master_servers_delete, name = 'master_servers_delete'),

    path('master/llms/', master_llms, name = 'master_llms'),
    path('master/llms_save/', master_llms_save, name = 'master_llms_save'),
    path('master/llms_delete/', master_llms_delete, name = 'master_llms_delete'),
    path('master/llmapis/', master_llmapis, name = 'master_llmapis'),
    path('master/llmapis_save/', master_llmapis_save, name = 'master_llmapis_save'),
    path('master/llmapis_delete/', master_llmapis_delete, name = 'master_llmapis_delete'),

    path('master/tenants/', master_tenants, name = 'master_tenants'),
    path('master/tenants_save/', master_tenants_save, name = 'master_tenants_save'),
    path('master/tenants_delete/', master_tenants_delete, name = 'master_tenants_delete'),

    path('master/tenant_users/', master_tenant_users, name = 'master_tenant_users'),
    path('master/tenant_users_save/', master_tenant_users_save, name = 'master_tenant_users_save'),
    path('master/tenant_users_delete/', master_tenant_users_delete, name = 'master_tenant_users_delete'),

    path('master/tenant_llms/', master_tenant_llms, name = 'master_tenant_llms'),
    path('master/tenant_llms_save/', master_tenant_llms_save, name = 'master_tenant_llms_save'),
    path('master/tenant_llms_delete/', master_tenant_llms_delete, name = 'master_tenant_llms_delete'),

    path('master/tenant_request/', master_tenant_request, name = 'master_tenant_request'),
    path('master/tenant_request_save/', master_tenant_request_save, name = 'master_tenant_request_save'),

    path('master/tenant_request_list/', master_tenant_request_list, name = 'master_tenant_request_list'),
    path('master/tenant_request_list_save/', master_tenant_request_list_save, name = 'master_tenant_request_list_save'),

    path('master/projects/', master_projects, name = 'master_projects'),
    path('master/projects_save/', master_projects_save, name = 'master_projects_save'),
    path('master/projects_delete/', master_projects_delete, name = 'master_projects_delete'),
    path('master/project_users/', master_project_users, name = 'master_project_users'),
    path('master_project_users_save/', master_project_users_save, name = 'master_project_users_save'),
    path('master_project_users_delete/', master_project_users_delete, name = 'master_project_users_delete'),

    path("api/send_verification_sms/", send_verification_sms, name = "send_verification_sms"),
    path("api/verify_sms_code/", verify_sms_code, name = "verify_sms_code"),
    path("api/check_verification_status/", check_verification_status, name="check_verification_status"),
    path("api/process_sms_verification/", process_sms_verification, name="process_sms_verification"),

    path('master/user_role/', master_user_role, name = 'master_user_role'),
    path('master/user_role_save/', master_user_role_save, name = 'master_user_role'),

    path('about_view/', about_view, name = 'about_view'),
    path('service_view/', service_view, name = 'service_view'),
    path('usage/', usage_view, name = 'usage_view'),
    path('qna_view/', qna_view, name = 'qna_view'),
    path('qna_save/', qna_save, name = 'qna_save'),
    path('qna_delete/', qna_delete, name = 'qna_delete'),
    path('qna_answer_save/', qna_answer_save, name = 'qna_answer_save'),
    path('qna_answer_delete/', qna_answer_delete, name = 'qna_answer_delete'),
    path('faq_view/', faq_view, name = 'faq_view'),
    path('faq_save/', faq_save, name = 'faq_save'),
    path('faq_delete/', faq_delete, name = 'faq_delete'),
    path('register_qna/', register_qna, name='register_qna'),
    path('register_qna/submit/', register_qna_submit, name='register_qna_submit'),

    path('myinfo/', myinfo, name='myinfo'),
    path('myinfo_update_username/', myinfo_update_username, name='myinfo_update_username'),
    path('myinfo_update_contact/', myinfo_update_contact, name = 'myinfo_update_contact'),
    path('password-reset/', password_reset, name='password_reset'),

    path('master/tables/', master_tables, name = 'master_tables'),
    path('master/tables_save/', master_tables_save, name = 'master_tables_save'),
    path('master/tables_delete/', master_tables_delete, name = 'master_tables_delete'),

    path('master/columns/', master_columns, name = 'master_columns'),
    path('master/columns_save/', master_columns_save, name = 'master_columns_save'),
    path('master/columns_delete/', master_columns_delete, name = 'master_columns_delete'),
    path('master/values_save/', master_values_save, name = 'master_values_save'),
    path('master/values_delete/', master_value_delete, name = 'master_value_delete'),

    path('master/rag_projects/', master_rag_projects, name = 'master_rag_projects'),
    path('master/rag_projects_save/', master_rag_projects_save, name = 'master_rag_projects_save'),
    path('master/rag_projects_delete/', master_rag_projects_delete, name = 'master_rag_projects_delete'),

    path('master/rag_projecttags/', master_rag_projecttags, name = 'master_rag_projecttags'),
    path('master/rag_projecttags_save/', master_rag_projecttags_save, name = 'master_rag_projecttags_save'),
    path('master/rag_projecttags_delete/', master_rag_projecttags_delete, name = 'master_rag_projecttags_delete'),

    path('master/rag_files/', master_rag_files, name = 'master_rag_files'),
    path('master/rag_files_save/', master_rag_files_save, name = 'master_rag_files_save'),
    path('master/rag_files_delete/', master_rag_files_delete, name = 'master_rag_files_delete'),

    path('master/rag_filemasters/', master_rag_filemasters, name = 'master_rag_filemasters'),
    path('master/rag_filemasters_save/', master_rag_filemasters_save, name = 'master_rag_filemasters_save'),
    path('master/rag_filemasters_delete/', master_rag_filemasters_delete, name = 'master_rag_filemasters_delete'),
]