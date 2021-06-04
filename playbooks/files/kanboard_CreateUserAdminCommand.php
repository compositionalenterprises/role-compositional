<?php

namespace Kanboard\Console;

use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Question\Question;
use Kanboard\Core\Security\Role;

class CreateUserAdminCommand extends BaseCommand
{
    protected function configure()
    {
        $this
            ->setName('user:create-admin')
            ->setDescription('Create Admin User')
            ->addArgument('username', InputArgument::REQUIRED, 'Username')
            ->addArgument('password', InputArgument::REQUIRED, 'Password')
            ->addArgument('email', InputArgument::REQUIRED, 'Email')
        ;
    }

    protected function execute(InputInterface $input, OutputInterface $output)
    {
        $helper = $this->getHelper('question');
        $username = $input->getArgument('username');
        $password = $input->getArgument('password');
        $email = $input->getArgument('email');

        // Call the function to actually create the user
        $this->createUserAdmin($output, $username, $password, $email);
    }

    private function createUserAdmin(OutputInterface $output, $username, $password, $email)
    {
        $values = array(
                'username' => $username,
                'password' => $password,
                'email' => $password,
                'role' => Role::APP_ADMIN,
                'is_ldap_user' => 0
        );
        //$project_id = empty($values['project_id']) ? 0 : $values['project_id'];
        $user_id = $this->userModel->create($values);
        if ($user_id !== false) {
            $output->writeln('<info>User Created Successfully</info>');
        } else {
            $output->writeln('<error>Unable to create your user.</error>');
            return false;
        }

        return true;
    }
}
