#!/bin/bash
#
# TaleTiles Control Script
#
# Manage the TaleTiles audiobook player service.
#
# Usage:
#   ./ctl.sh start|stop|restart|status|logs|test
#

SERVICE_NAME="taletiles"

case "$1" in
    start)
        echo "Starting TaleTiles..."
        sudo systemctl start $SERVICE_NAME
        sleep 2
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;

    stop)
        echo "Stopping TaleTiles..."
        sudo systemctl stop $SERVICE_NAME
        echo "Stopped."
        ;;

    restart)
        echo "Restarting TaleTiles..."
        sudo systemctl restart $SERVICE_NAME
        sleep 2
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;

    status)
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;

    logs)
        echo "Showing TaleTiles logs (Ctrl+C to exit)..."
        journalctl -u $SERVICE_NAME -f
        ;;

    test)
        echo "Running TaleTiles in test mode..."
        echo "Press Ctrl+C to stop."
        echo ""
        cd "$(dirname "$0")"
        source venv/bin/activate
        python player.py
        ;;

    add)
        echo "Adding a new audiobook..."
        cd "$(dirname "$0")"
        source venv/bin/activate
        python add_book.py
        ;;

    list)
        echo "Registered audiobooks:"
        cd "$(dirname "$0")"
        source venv/bin/activate
        python add_book.py --list
        ;;

    check)
        echo "Checking configuration..."
        cd "$(dirname "$0")"
        source venv/bin/activate
        python add_book.py --check
        ;;

    *)
        echo "TaleTiles Control Script"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Service commands:"
        echo "  start     Start the TaleTiles service"
        echo "  stop      Stop the TaleTiles service"
        echo "  restart   Restart the TaleTiles service"
        echo "  status    Show service status"
        echo "  logs      Follow service logs"
        echo ""
        echo "Development commands:"
        echo "  test      Run player in foreground (for testing)"
        echo ""
        echo "Audiobook commands:"
        echo "  add       Register a new audiobook"
        echo "  list      List registered audiobooks"
        echo "  check     Check for configuration issues"
        exit 1
        ;;
esac
