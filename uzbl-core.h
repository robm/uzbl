/* -*- c-basic-offset: 4; -*-

 * See LICENSE for license details
 *
 * Changelog:
 * ---------
 *
 * (c) 2009 by Robert Manea
 *     - introduced struct concept
 *     - statusbar template
 *
 */

/* status bar elements */
typedef struct {
    gint           load_progress;
    gchar          *msg;
} StatusBar;


/* gui elements */
typedef struct {
    GtkWidget*     main_window;
    gchar*         geometry;
    GtkPlug*       plug;
    GtkWidget*     scrolled_win;
    GtkWidget*     vbox;
    GtkWidget*     mainbar;
    GtkWidget*     mainbar_label;
    GtkScrollbar*  scbar_v;   // Horizontal and Vertical Scrollbar
    GtkScrollbar*  scbar_h;   // (These are still hidden)
    GtkAdjustment* bar_v; // Information about document length
    GtkAdjustment* bar_h; // and scrolling position
    WebKitWebView* web_view;
    gchar*         main_title;
    gchar*         icon;

    /* WebInspector */
    GtkWidget *inspector_window;
    WebKitWebInspector *inspector;

    StatusBar sbar;
} GUI;


/* external communication*/
enum { FIFO, SOCKET};
typedef struct {
    gchar          *fifo_path;
    gchar          *socket_path;
    /* stores (key)"variable name" -> (value)"pointer to this var*/
    GHashTable     *proto_var;

    gchar          *sync_stdout;
    GIOChannel     *clientchan;
    GIOChannel     *fifo_chan;
    GIOChannel     *socket_chan;
    GIOChannel     *stdin_chan;
    guint           stdin_watch_id;
} Communication;


/* internal state */
typedef struct {
    gchar    *uri;
    gchar    *config_file;
    int      socket_id;
    char     *instance_name;
    gchar    *selected_url;
    gchar    *last_selected_url;
    gchar    *executable_path;
    gchar*   keycmd;
    gchar*   searchtx;
    gboolean verbose;
    GPtrArray *event_buffer;
    gchar    *event_response;
} State;


/* networking */
typedef struct {
    SoupSession *soup_session;
    SoupLogger *soup_logger;
    char *proxy_url;
    char *useragent;
    gint max_conns;
    gint max_conns_host;
} Network;


/* behaviour */
typedef struct {
    gchar*   load_finish_handler;
    gchar*   load_start_handler;
    gchar*   load_commit_handler;
    gchar*   status_format;
    gchar*   title_format_short;
    gchar*   title_format_long;
    gchar*   status_background;
    gchar*   fifo_dir;
    gchar*   socket_dir;
    gchar*   download_handler;
    gchar*   cookie_handler;
    gchar*   new_window;
    gchar*   default_font_family;
    gchar*   monospace_font_family;
    gchar*   sans_serif_font_family;
    gchar*   serif_font_family;
    gchar*   fantasy_font_family;
    gchar*   cursive_font_family;
    gchar*   scheme_handler;
    gboolean show_status;
    gboolean forward_keys;
    gboolean status_top;
    guint    modmask;
    guint    http_debug;
    gchar*   shell_cmd;
    guint    view_source;
    /* WebKitWebSettings exports */
    guint    font_size;
    guint    monospace_size;
    guint    minimum_font_size;
    gfloat   zoom_level;
    guint    disable_plugins;
    guint    disable_scripts;
    guint    autoload_img;
    guint    autoshrink_img;
    guint    enable_spellcheck;
    guint    enable_private;
    guint    print_bg;
    gchar*   style_uri;
    guint    resizable_txt;
    gchar*   default_encoding;
    guint    enforce_96dpi;
    gchar    *inject_html;
    guint    caret_browsing;
    guint    mode;
    gchar*   base_url;
    gboolean print_version;

    /* command list: (key)name -> (value)Command  */
    /* command list: (key)name -> (value)Command  */
    GHashTable* commands;
    /* event lookup: (key)event_id -> (value)event_name */
    GHashTable *event_lookup;
} Behaviour;

/* javascript */
typedef struct {
    gboolean            initialized;
    JSClassDefinition   classdef;
    JSClassRef          classref;
} Javascript;

/* static information */
typedef struct {
    int   webkit_major;
    int   webkit_minor;
    int   webkit_micro;
    gchar *arch;
    gchar *commit;
    gchar *pid_str;
} Info;

/* main uzbl data structure */
typedef struct {
    GUI           gui;
    State         state;
    Network       net;
    Behaviour     behave;
    Communication comm;
    Javascript    js;
    Info          info;

    Window        xwin;
} UzblCore;


typedef struct {
    char* name;
    char* param;
} Action;

typedef void sigfunc(int);

/* Event system */
enum event_type {
    LOAD_START, LOAD_COMMIT, LOAD_FINISH, LOAD_ERROR,
    KEY_PRESS, KEY_RELEASE, DOWNLOAD_REQ, COMMAND_EXECUTED,
    LINK_HOVER, TITLE_CHANGED, GEOMETRY_CHANGED, 
    WEBINSPECTOR, NEW_WINDOW, SELECTION_CHANGED,
    VARIABLE_SET, FIFO_SET, SOCKET_SET, 
    INSTANCE_START, INSTANCE_EXIT, LOAD_PROGRESS,
    LINK_UNHOVER,
    
    /* must be last entry */
    LAST_EVENT
};

/* XDG Stuff */
typedef struct {
    gchar* environmental;
    gchar* default_value;
} XDG_Var;

XDG_Var XDG[] =
{
    { "XDG_CONFIG_HOME", "~/.config" },
    { "XDG_DATA_HOME",   "~/.local/share" },
    { "XDG_CACHE_HOME",  "~/.cache" },
    { "XDG_CONFIG_DIRS", "/etc/xdg" },
    { "XDG_DATA_DIRS",   "/usr/local/share/:/usr/share/" },
};

/* Functions */
char *
itos(int val);

char *
str_replace (const char* search, const char* replace, const char* string);

GArray*
read_file_by_line (const gchar *path);

gchar*
parseenv (char* string);

void
clean_up(void);

void
catch_sigterm(int s);

sigfunc *
setup_signal(int signe, sigfunc *shandler);

gboolean
set_var_value(const gchar *name, gchar *val);

void
print(WebKitWebView *page, GArray *argv, GString *result);

gboolean
navigation_decision_cb (WebKitWebView *web_view, WebKitWebFrame *frame, WebKitNetworkRequest *request, WebKitWebNavigationAction *navigation_action, WebKitWebPolicyDecision *policy_decision, gpointer user_data);

gboolean
new_window_cb (WebKitWebView *web_view, WebKitWebFrame *frame, WebKitNetworkRequest *request, WebKitWebNavigationAction *navigation_action, WebKitWebPolicyDecision *policy_decision, gpointer user_data);

gboolean
mime_policy_cb(WebKitWebView *web_view, WebKitWebFrame *frame, WebKitNetworkRequest *request, gchar *mime_type,  WebKitWebPolicyDecision *policy_decision, gpointer user_data);

/*@null@*/ WebKitWebView*
create_web_view_cb (WebKitWebView  *web_view, WebKitWebFrame *frame, gpointer user_data);

gboolean
download_cb (WebKitWebView *web_view, GObject *download, gpointer user_data);

void
toggle_zoom_type (WebKitWebView* page, GArray *argv, GString *result);

void
toggle_status_cb (WebKitWebView* page, GArray *argv, GString *result);

void
link_hover_cb (WebKitWebView* page, const gchar* title, const gchar* link, gpointer data);

void
title_change_cb (WebKitWebView* web_view, GParamSpec param_spec);

void
progress_change_cb (WebKitWebView* page, gint progress, gpointer data);

void
load_commit_cb (WebKitWebView* page, WebKitWebFrame* frame, gpointer data);

void
load_start_cb (WebKitWebView* page, WebKitWebFrame* frame, gpointer data);

void
load_finish_cb (WebKitWebView* page, WebKitWebFrame* frame, gpointer data);

void
selection_changed_cb(WebKitWebView *webkitwebview, gpointer ud);

void
destroy_cb (GtkWidget* widget, gpointer data);

void
commands_hash(void);

void
free_action(gpointer act);

Action*
new_action(const gchar *name, const gchar *param);

bool
file_exists (const char * filename);

void
set_keycmd();

void
load_uri (WebKitWebView * web_view, GArray *argv, GString *result);

void
new_window_load_uri (const gchar * uri);

void
chain (WebKitWebView *page, GArray *argv, GString *result);

void
close_uzbl (WebKitWebView *page, GArray *argv, GString *result);

gboolean
run_command(const gchar *command, const guint npre,
            const gchar **args, const gboolean sync, char **output_stdout);

void
talk_to_socket(WebKitWebView *web_view, GArray *argv, GString *result);

void
spawn(WebKitWebView *web_view, GArray *argv, GString *result);

void
spawn_sh(WebKitWebView *web_view, GArray *argv, GString *result);

void
spawn_sync(WebKitWebView *web_view, GArray *argv, GString *result);

void
spawn_sh_sync(WebKitWebView *web_view, GArray *argv, GString *result);

void
parse_command(const char *cmd, const char *param, GString *result);

void
parse_cmd_line(const char *ctl_line, GString *result);

/*@null@*/ gchar*
build_stream_name(int type, const gchar *dir);

gboolean
control_fifo(GIOChannel *gio, GIOCondition condition);

/*@null@*/ gchar*
init_fifo(gchar *dir);

gboolean
control_stdin(GIOChannel *gio, GIOCondition condition);

void
create_stdin();

/*@null@*/ gchar*
init_socket(gchar *dir);

gboolean
control_socket(GIOChannel *chan);

gboolean
control_client_socket(GIOChannel *chan);

void
update_title (void);

gboolean
key_press_cb (GtkWidget* window, GdkEventKey* event);

gboolean
key_release_cb (GtkWidget* window, GdkEventKey* event);

void
run_keycmd(const gboolean key_ret);

void
initialize (int argc, char *argv[]);

void
create_browser ();

GtkWidget*
create_mainbar ();

GtkWidget*
create_window ();

GtkPlug*
create_plug ();

void
run_handler (const gchar *act, const gchar *args);

/*@null@*/ gchar*
get_xdg_var (XDG_Var xdg);

/*@null@*/ gchar*
find_xdg_file (int xdg_type, const char* filename);

void
settings_init ();

void
search_text (WebKitWebView *page, GArray *argv, const gboolean forward);

void
search_forward_text (WebKitWebView *page, GArray *argv, GString *result);

void
search_reverse_text (WebKitWebView *page, GArray *argv, GString *result);

void
dehilight (WebKitWebView *page, GArray *argv, GString *result);

void
run_js (WebKitWebView * web_view, GArray *argv, GString *result);

void
run_external_js (WebKitWebView * web_view, GArray *argv, GString *result);

void
eval_js(WebKitWebView * web_view, gchar *script, GString *result);

void handle_cookies (SoupSession *session,
                            SoupMessage *msg,
                            gpointer     user_data);
void
save_cookies (SoupMessage *msg, gpointer     user_data);

void
set_var(WebKitWebView *page, GArray *argv, GString *result);

void
act_dump_config();

void
act_dump_config_as_events();

void
dump_var_hash(gpointer k, gpointer v, gpointer ud);

void
dump_key_hash(gpointer k, gpointer v, gpointer ud);

void
dump_config();

void
dump_config_as_events();

void
retrieve_geometry();

void
update_gui(WebKitWebView *page, GArray *argv, GString *result);

void
event(WebKitWebView *page, GArray *argv, GString *result);

gboolean
configure_event_cb(GtkWidget* window, GdkEventConfigure* event);

typedef void (*Command)(WebKitWebView*, GArray *argv, GString *result);
typedef struct {
    Command function;
    gboolean no_split;
} CommandInfo;

/* Command callbacks */
void
cmd_load_uri();

void
cmd_set_status();

void
set_proxy_url();

void
set_icon();

void
cmd_cookie_handler();

void
cmd_scheme_handler();

void
move_statusbar();

void
cmd_http_debug();

void
cmd_max_conns();

void
cmd_max_conns_host();

/* exported WebKitWebSettings properties */

void
cmd_font_size();

void
cmd_default_font_family();

void
cmd_monospace_font_family();

void
cmd_sans_serif_font_family();

void
cmd_serif_font_family();

void
cmd_cursive_font_family();

void
cmd_fantasy_font_family();

void
cmd_zoom_level();

void
cmd_disable_plugins();

void
cmd_disable_scripts();

void
cmd_minimum_font_size();

void
cmd_fifo_dir();

void
cmd_socket_dir();

void
cmd_useragent() ;

void
cmd_autoload_img();

void
cmd_autoshrink_img();

void
cmd_enable_spellcheck();

void
cmd_enable_private();

void
cmd_print_bg();

void
cmd_style_uri();

void
cmd_resizable_txt();

void
cmd_default_encoding();

void
cmd_enforce_96dpi();

void
cmd_inject_html();

void
cmd_caret_browsing();

void
cmd_set_geometry();

/*
void
cmd_view_source();
*/

void
cmd_load_start();

/* vi: set et ts=4: */
