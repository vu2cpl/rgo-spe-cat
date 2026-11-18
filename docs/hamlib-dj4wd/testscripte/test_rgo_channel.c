/*
 * test_rgo_channel.c -- direct test of the RGO ONE V6 channel backend
 * (set_channel / get_channel / delete_channel incl. MR readback).
 *
 * Hamlib 4.7.1 never calls caps->delete_channel, and rigctl/rigctld cannot
 * forward channel operations. This program talks to the backend directly.
 * No transmit commands are sent. Not part of the patch.
 *
 * Build:  gcc -o test_rgo_channel test_rgo_channel.c $(pkg-config --cflags --libs hamlib)
 * Usage:  ./test_rgo_channel [-r DEV] [-s BAUD] [-c CH] MODE
 *   MODE write    set_channel + get_channel verify, channel is left written
 *        delete   delete_channel + get_channel must give -RIG_ENAVAIL
 *        memmode  rig in MEMORY mode (display "CH nn"), channel written
 *                 before: set_channel and delete_channel must both return
 *                 -RIG_ERJCTED and leave the channel unchanged
 *        all      write, then delete
 * write/all refuse to run if the test channel is not empty.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <hamlib/rig.h>

#define TEST_FREQ 7074000.0

static int failures;

static void check(int cond, const char *what, int rc)
{
    printf("  [%s] %s (rc=%d %s)\n", cond ? "OK" : "FAIL", what, rc,
           rc < 0 ? rigerror(rc) : "");

    if (!cond) { failures++; }
}

static void init_chan(channel_t *c, int ch, freq_t f)
{
    memset(c, 0, sizeof(*c));
    c->channel_num = ch;
    c->vfo   = RIG_VFO_MEM;
    c->freq  = f;
    c->mode  = RIG_MODE_USB;
    c->width = 2700;
    c->split = RIG_SPLIT_OFF;
}

static int do_get(RIG *rig, int ch, channel_t *out)
{
    memset(out, 0, sizeof(*out));
    out->channel_num = ch;
    return rig_get_channel(rig, RIG_VFO_CURR, out, 1);
}

static void step_write(RIG *rig, int ch)
{
    channel_t c, rb;
    int rc;

    printf("write: set_channel ch%02d %.0f Hz USB\n", ch, TEST_FREQ);
    init_chan(&c, ch, TEST_FREQ);
    rc = rig_set_channel(rig, RIG_VFO_CURR, &c);
    check(rc == RIG_OK, "set_channel", rc);

    rc = do_get(rig, ch, &rb);
    check(rc == RIG_OK && (long long) rb.freq == (long long) TEST_FREQ
          && rb.mode == RIG_MODE_USB, "get_channel readback matches", rc);
}

static void step_delete(RIG *rig, int ch)
{
    channel_t c, rb;
    int rc;

    printf("delete: caps->delete_channel ch%02d\n", ch);
    init_chan(&c, ch, 0);
    rc = rig->caps->delete_channel(rig, RIG_VFO_CURR, &c);
    check(rc == RIG_OK, "delete_channel", rc);

    rc = do_get(rig, ch, &rb);
    check(rc == -RIG_ENAVAIL, "get_channel reports empty (-RIG_ENAVAIL)", rc);
}

static void step_memmode(RIG *rig, int ch)
{
    channel_t c, rb;
    int rc;

    printf("memmode: rig must show \"CH nn\"; channel %02d must be written\n", ch);
    rc = do_get(rig, ch, &rb);
    check(rc == RIG_OK, "precondition: channel has data", rc);

    if (rc != RIG_OK) { return; }

    init_chan(&c, ch, TEST_FREQ + 26000.0);
    rc = rig_set_channel(rig, RIG_VFO_CURR, &c);
    check(rc == -RIG_ERJCTED, "set_channel rejected in memory mode", rc);

    init_chan(&c, ch, 0);
    rc = rig->caps->delete_channel(rig, RIG_VFO_CURR, &c);
    check(rc == -RIG_ERJCTED, "delete_channel rejected in memory mode", rc);

    rc = do_get(rig, ch, &rb);
    check(rc == RIG_OK && (long long) rb.freq == (long long) TEST_FREQ,
          "channel unchanged", rc);
}

int main(int argc, char **argv)
{
    const char *dev = "/dev/ttyACM0", *baud = "9600", *mode = NULL;
    int ch = 99, i, rc;
    RIG *rig;
    channel_t probe;

    for (i = 1; i < argc; i++)
    {
        if (!strcmp(argv[i], "-r") && i + 1 < argc) { dev = argv[++i]; }
        else if (!strcmp(argv[i], "-s") && i + 1 < argc) { baud = argv[++i]; }
        else if (!strcmp(argv[i], "-c") && i + 1 < argc) { ch = atoi(argv[++i]); }
        else { mode = argv[i]; }
    }

    if (!mode || ch < 1 || ch > 99)
    {
        fprintf(stderr, "usage: %s [-r DEV] [-s BAUD] [-c CH 1-99] write|delete|memmode|all\n",
                argv[0]);
        return 2;
    }

    rig_set_debug(RIG_DEBUG_ERR);
    rig_load_all_backends();
    rig = rig_init(43001);

    if (!rig) { fprintf(stderr, "rig_init failed\n"); return 2; }

    rig_set_conf(rig, rig_token_lookup(rig, "rig_pathname"), dev);
    rig_set_conf(rig, rig_token_lookup(rig, "serial_speed"), baud);

    rc = rig_open(rig);

    if (rc != RIG_OK)
    {
        fprintf(stderr, "rig_open: %s\n", rigerror(rc));
        return 2;
    }

    printf("RGO ONE V6, %s @ %s, test channel %02d, mode %s\n", dev, baud, ch, mode);

    if (!strcmp(mode, "write") || !strcmp(mode, "all"))
    {
        rc = do_get(rig, ch, &probe);

        if (rc != -RIG_ENAVAIL)
        {
            fprintf(stderr, "channel %02d is not empty (rc=%d) -- refusing to overwrite\n",
                    ch, rc);
            rig_close(rig);
            rig_cleanup(rig);
            return 2;
        }

        step_write(rig, ch);
    }

    if (!strcmp(mode, "delete") || !strcmp(mode, "all")) { step_delete(rig, ch); }

    if (!strcmp(mode, "memmode")) { step_memmode(rig, ch); }

    rig_close(rig);
    rig_cleanup(rig);
    printf("%s\n", failures ? "RESULT: FAILED" : "RESULT: OK");
    return failures ? 1 : 0;
}
