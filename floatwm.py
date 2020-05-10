import i3, subprocess
from typing import List, Dict
import sys, os
from collections import namedtuple

RC_FILE_NAME = '.floatrc'
DISPLAY_MONITORS = {
    "eDP1",
    "HDMI1",
    "VGA",
}
# Custom Types
# The x and y coordinates of any X11 object
Location = namedtuple('Location', 'width height')
# A vector of location objects
Tensor = List[Location]
# Represents the display monitor to their respective index
DisplayMap = Dict[int, Location]

# TODO: replace global variables with rc file
# TODO: handle multiple monitor (behind summation) offset
# TODO: add grid options

class Utils:
    def __init__(self, ):
        super().__init__()

    @staticmethod
    def dipatch_bash_command(command_str: str) -> str:
        if (not command_str or
           command_str.strip() == ""): raise ValueError("null command")

        out = subprocess.run(command_str.split(" "), stdout=subprocess.PIPE)
        return out.stdout

    @staticmethod
    def dispatch_i3msg_com(command: str, data:Location=Location(1189, 652)):
        # Immutable location tuple accounts for mutation error
        if not isinstance(data, (list, tuple)) and len(data) == 2:
            raise ValueError("Incorrect data type/length for i3 command")
        w = str(data.width) if data.width > 0 else '0'
        h = str(data.height) if data.height > 0 else '0'
        if command == 'resize':
            # 1189, 652 is a standard i3 window size for floating nodes
            # Data should be a len(Vector) == 2 (width, height)
            return i3.resize('set', w, h)
        if command == 'move':
            print(f'w: {w}, h: {h}"')
            return i3.move('window', 'position', w, h)
        if command == 'float':
            return i3.floating('toggle')


    @staticmethod
    def get_cmd_args(elem=None):
        try:
            if elem:
                if elem > len(sys.argv[1:]):
                    return None
                elif len(sys.argv[1:]) < 2:
                    return [4, 4][elem]
                return int(sys.argv[elem])
            else:
                return [int(i) for i in sys.argv[1:]] or [4, 4]
        except ValueError:
            return [4, 4]

    @staticmethod
    def read_config():
        default_locs = [
            '~/.config/i3float/floatrc'
            '~/.config/floatrc',
            '~/.floatrc',
                os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                RC_FILE_NAME)
        ]
        target_loc = None
        for loc in default_locs:
            if os.path.isfile(loc):
                target_loc = loc
                break

        if not target_loc:
            raise ValueError("No dotfile config found. " \
                             "Add to ~/.floatrc or ~/.config/floatrc " \
                             "or ~/.config/i3float/floatrc")


class FloatUtils:
    def __init__(self):
        self.area_matrix, self.current_display = self._calc_metadata()
        assert len(self.current_display) > 0, "Incorrect Display Input"
        # self.current_display = self.current_display

    def _calc_metadata(self) -> (DisplayMap, dict):
        self.displays = i3.get_outputs()

        # Widths * Lengths (seperated to retain composition for children)
        total_size = {}
        monitor_cnt = 0
        for display in self.displays:
            if display['name'] not in DISPLAY_MONITORS:
                continue
            # print(display)
            display_screen_location = Location(
                    width=display['rect']['width'],
                    height=display['rect']['height'])
            total_size[monitor_cnt] = display_screen_location
            monitor_cnt += 1

            # total_size[0] += [display['rect']['width']]
            # total_size[1] += [display['rect']['height']]
        active = [i for i in i3.get_workspaces() if i['focused']][0]
        return total_size, active

    def get_i3_socket(self):
        socket = i3.Socket()


class MonitorCalculator:
    def __init__(self, ):
        super().__init__()

    def get_offset(self, window: Location, target: Location) -> Location:
        # 1) Calculate monitor center
        # 2) Calculate window offset
        # 3) Monitor center - offset = true center
        # 3 if) tensors are intersecting
        display_offset, target_offset = self.get_screen_center(
                window, target)
        center_x = display_offset.width - target_offset.width
        # Heigh is half of the respective monitor
        # The tensors are parallel hence, no summation.
        center_y = display_offset.height

        return Location(center_x, center_y)


    def get_screen_center(self, *windows: Location) -> Location:
        return [Location(int(window.width/2), int(window.height/2))
                for window in windows]

class Movements:
    def __init__(self, ):
        super().__init__()

class FloatManager(FloatUtils, MonitorCalculator):
    def __init__(self, rows=2, cols=2, target=0):
        super().__init__()
        if target == 0:
            self.make_float()
            self.move_to_center()
        self.rows = rows
        self.cols = cols
        self.target = target

    def move_to_center(self):
        workspace_num = self.get_wk_number()
        # Get the focused node
        self.assign_focus_node()
        # print(self.focused_node)

        # we call the focused node the target
        target_pos = Location(width=self.focused_node['rect']['width'],
                 height=self.focused_node['rect']['height'])
        print('target:', target_pos)

        # True center (accounting for multiple displays)
        true_center = self.get_offset(window=self.area_matrix[workspace_num],
                                      target=target_pos)
        print('true:', true_center)
        print('matrix', self.area_matrix)
        # TODO
        # Apply offset (user preference (due to polybar, etc.))

        # Dispatch final command
        Utils.dispatch_i3msg_com(command="move", data=true_center)

    def make_float(self):
        Utils.dispatch_i3msg_com(command='float')
        pass

    def assign_focus_node(self):
        tree = i3.get_tree()
        # for node in tree:
        wkspc = [node for node in tree['nodes']
                if node['name'] == self.current_display['output']]
        assert len(wkspc) > 0, "window could not be found"
        # wkspc = wkspc[0]
        self.iter = 0
        for w in wkspc:
            self.find_focused_window(w)

    def find_focused_window(self, node):
        # DFS to find the current window
        self.iter += 1
        if not isinstance(node, dict): return
        if node['focused']:
            self.focused_node = node
            return

        if (len(node['nodes']) != 0) or (len(node['floating_nodes']) != 0):
            target_nodes = node['nodes'] + node['floating_nodes']
            for root in target_nodes: self.find_focused_window(root)
        else: return

    def get_wk_number(self):
        c_monitor = 0
        for display in self.displays:
            if display['name'] in DISPLAY_MONITORS:
                if self.match(display): break
                c_monitor += 1
        return c_monitor

    def match(self, display):
        validations = [
            ['name', 'output'],
            ['current_workspace', 'name'],
            'rect'
        ]
        for val in validations:
            if val == 'rect':
                if (display[val]['width'] !=
                    self.current_display[val]['width']):
                    return False
            elif display[val[0]] != self.current_display[val[1]]:
                return False
        return True

        # for d, t in in zip(display, self.current_display):
            # if

def debugger():
    print("Entering debug mode. Evaluating input:")
    while 1:
        cmd = input('>>> ')
        print(eval(cmd))

if __name__ == "__main__":
    if "debug" in sys.argv:
        debugger()
        exit(0)


