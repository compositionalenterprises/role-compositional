<?php
declare(strict_types=1);

namespace FireflyIII\Console\Commands;

use FireflyIII\Repositories\User\UserRepositoryInterface;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

/**
 * Class CreateUser
 * @package FireflyIII\Console\Commands
 */
class CreateUser extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'firefly-iii:create-user {email} {password}';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Creates a new admin user. Takes the email address and password.';

    private UserRepositoryInterface $repository;

    /**
     * Create a new command instance.
     *
     * @return void
     */
    public function __construct()
    {
        parent::__construct();
    }

    /**
     * Execute the console command.
     *
     * @return int
     */
    public function handle(): int
    {
        $this->stupidLaravel();
        $data           = [
            'blocked'      => false,
            'blocked_code' => null,
            'email'        => $this->argument('email'),
            'role'         => 'owner',
        ];
        $user           = $this->repository->store($data);
        $password       = $this->argument('password');
        $user->password = Hash::make($password);
        $user->save();
        $user->setRememberToken(Str::random(60));

        $this->info(sprintf('Created new admin user (ID #%d) with email address "%s" and password (hidden).', $user->id, $user->email, $password));
        return 0;
    }

    /**
     * Laravel will execute ALL __construct() methods for ALL commands whenever a SINGLE command is
     * executed. This leads to noticeable slow-downs and class calls. To prevent this, this method should
     * be called from the handle method instead of using the constructor to initialize the command.
     *
     * @codeCoverageIgnore
     */
    private function stupidLaravel(): void
    {
        $this->repository = app(UserRepositoryInterface::class);

    }
}
